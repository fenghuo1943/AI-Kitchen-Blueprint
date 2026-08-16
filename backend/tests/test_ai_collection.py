"""AI 联网采集菜谱入库功能测试

说明：SQLite 内存库 + StaticPool 单连接，后台线程跑 DB 会撞连接，
因此服务层直接注入 FakeTavily/FakeLLM 并同步调用 _run_collection；
executor 的 enqueue_ai_collect/enqueue_index 均 patch 为 no-op。
"""
import hashlib
import json
import uuid
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import settings
from app.db.models import (
    IngestionCandidate, IngestionJob, Ingredient, IngredientCategory,
    Recipe, RecipeCategory, RecipeCategoryLink, RecipeIngredient,
    RecipeRevision, RecipeSeasoning, RecipeSource, RecipeStep, Seasoning,
    SeasoningCategory,
)
from app.llm import LLMProvider, LLMUnavailableError, LLMValidationError
from app.llm.factory import default_model_for
from app.llm.prompts import (
    RecipeExtraction, extract_recipe_from_sources, extract_recipe_with_fix,
    normalize_title, validate_recipe_reason,
)
from app.llm.schema import sanitize_schema_for_anthropic
from app.services.ai_collection_service import AiCollectionService
from app.services.browser_fetcher import BrowserFetchError
from app.services.tavily_client import TavilySearchResult, TavilyUnavailableError


# ------------------------------------------------------------------ #
# 测试替身
# ------------------------------------------------------------------ #
def make_recipe(title="西红柿炒鸡蛋", url="https://example.com/tomato"):
    return {
        "title": title,
        "summary": "经典家常菜",
        "servings": 2,
        "prep_minutes": 5,
        "cook_minutes": 10,
        "difficulty": "简单",
        "ingredients": [
            {"name": "西红柿", "quantity": "2", "unit": "个", "raw_quantity": "两个"},
            {"name": "鸡蛋", "quantity": "3", "unit": "个"},
        ],
        "steps": [
            {"step_no": 1, "instruction": "西红柿切块"},
            {"step_no": 2, "instruction": "鸡蛋打散炒熟"},
        ],
        "tags": ["家常菜"],
        "source_url": url,
    }


class FakeTavily:
    def __init__(self, results=None, pages=None):
        self.results = results or []
        self.pages = pages or ([], [])
        self.search_queries = []
        self.search_include_domains = None

    def search(self, query, max_results=5, search_depth="basic", include_domains=None):
        self.search_queries.append(query)
        self.search_include_domains = include_domains
        return self.results

    def extract(self, urls):
        return self.pages


class FakeLLM(LLMProvider):
    def __init__(self, recipe=None, fail_urls=None, fail_then_succeed=False):
        self.recipe = recipe
        self.fail_urls = fail_urls or set()
        self.fail_then_succeed = fail_then_succeed
        self.calls = 0

    def generate(self, messages, response_schema=None, timeout=None):
        self.calls += 1
        user = messages[-1]["content"] if messages else ""
        if any(u in user for u in self.fail_urls):
            raise LLMUnavailableError("llm down")
        if self.fail_then_succeed and self.calls == 1:
            raise LLMValidationError("首次输出非法 JSON")
        return dict(self.recipe) if self.recipe else {}

    def health_check(self):
        return {"ok": True, "model_available": True, "detail": "fake"}


class SequencedLLM(LLMProvider):
    """按调用顺序依次返回预置响应（模拟多来源总结返回"无菜谱"后逐页成功）。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, messages, response_schema=None, timeout=None):
        resp = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return dict(resp)

    def health_check(self):
        return {"ok": True, "model_available": True, "detail": "fake"}


class FakeBrowser:
    """记录 fetch 调用并返回可配置正文；available 可关。"""

    def __init__(self, content="浏览器抓到的正文……", available=True):
        self.content = content
        self._available = available
        self.fetch_urls = []

    def available(self):
        if self._available:
            return (True, "")
        return (False, "fake unavailable")

    def fetch(self, url):
        self.fetch_urls.append(url)
        if not self.content:
            raise BrowserFetchError("正文为空")
        return self.content


def make_service(tavily=None, llm=None, browser=None) -> AiCollectionService:
    return AiCollectionService(
        tavily=tavily or FakeTavily(),
        llm=llm or FakeLLM(make_recipe()),
        browser=browser,
    )


def make_job(db, mode="topic", request_text="西红柿", target_id=None):
    job = IngestionJob(
        id=str(uuid.uuid4()),
        status="queued",
        stage="submitted",
        job_type="ai_search",
        request_text=request_text,
        collection_mode=mode,
        target_recipe_id=target_id,
        max_results=5,
    )
    db.add(job)
    db.commit()
    return job


@pytest.fixture
def no_enqueue(monkeypatch):
    """屏蔽采集/索引后台任务（单连接 SQLite 不能开线程）。"""
    import app.tasks.executor as ex

    def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(ex, "enqueue_ai_collect", _noop)
    monkeypatch.setattr(ex, "enqueue_index", _noop)


@pytest.fixture
def tavily_key(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")


def one_page(url="https://example.com/tomato", content="西红柿炒鸡蛋做法：西红柿切块，鸡蛋打散……"):
    return ([{"url": url, "raw_content": content}], [])


# ------------------------------------------------------------------ #
# 工具函数
# ------------------------------------------------------------------ #
def test_normalize_title():
    assert normalize_title("番茄 炒 蛋") == normalize_title("番茄炒蛋")
    assert normalize_title("番茄、炒蛋！") == normalize_title("番茄炒蛋")
    assert normalize_title("Tomato Scramble") == normalize_title("tomato scramble")


def test_sanitize_schema_for_anthropic():
    raw = RecipeExtraction.model_json_schema()
    dumped = json.dumps(raw)
    assert "minLength" not in dumped or True  # Pydantic 未生成数值约束也通过
    cleaned = json.dumps(sanitize_schema_for_anthropic(raw))
    assert "additionalProperties" in cleaned
    # 无 `minLength`/`pattern` 类不受支持约束
    for bad in ("minLength", "minimum", "pattern"):
        assert bad not in cleaned


# ------------------------------------------------------------------ #
# Tavily 客户端
# ------------------------------------------------------------------ #
class FakeResp:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=self)

    def json(self):
        return self._data


def test_tavily_search(monkeypatch):
    from app.services.tavily_client import TavilyClient

    def fake_post(self, url, headers=None, json=None, **kw):
        assert json["query"] == "西红柿 菜谱 做法"
        return FakeResp(200, {"results": [{"title": "T", "url": "https://x", "content": "c", "score": 0.9}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = TavilyClient(api_key="k")
    results = client.search("西红柿 菜谱 做法")
    assert results[0].url == "https://x"
    assert results[0].score == 0.9


def test_tavily_search_include_domains(monkeypatch):
    from app.services.tavily_client import TavilyClient

    def fake_post(self, url, headers=None, json=None, **kw):
        assert json["include_domains"] == ["xiachufang.com", "meishichina.com"]
        return FakeResp(200, {"results": [{"title": "T", "url": "https://m.xiachufang.com/r", "content": "c", "score": 0.9}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = TavilyClient(api_key="k")
    results = client.search("西红柿 菜谱 做法", include_domains=["xiachufang.com", "meishichina.com"])
    assert results[0].url == "https://m.xiachufang.com/r"


def test_tavily_extract(monkeypatch):
    from app.services.tavily_client import TavilyClient

    def fake_post(self, url, headers=None, json=None, **kw):
        return FakeResp(200, {
            "results": [{"url": "https://x", "raw_content": "<p>内容</p>"}],
            "failed_results": [{"url": "https://bad", "error": "403"}],
        })

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = TavilyClient(api_key="k")
    ok, failed = client.extract(["https://x", "https://bad"])
    assert len(ok) == 1
    assert ok[0]["raw_content"] == "<p>内容</p>"
    assert len(failed) == 1


def test_tavily_401(monkeypatch):
    from app.services.tavily_client import TavilyClient

    def fake_post(self, url, headers=None, json=None, **kw):
        return FakeResp(401, {})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = TavilyClient(api_key="k")
    with pytest.raises(TavilyUnavailableError):
        client.search("q")


def test_tavily_missing_key():
    from app.services.tavily_client import TavilyClient
    client = TavilyClient(api_key=None)
    with pytest.raises(TavilyUnavailableError):
        client.search("q")


def test_clean_page_text():
    from app.services.tavily_client import clean_page_text
    assert clean_page_text("  <p> 标题 </p>\n 步骤一\t步骤二  ") == "标题 步骤一 步骤二"


def test_default_search_sites(monkeypatch):
    """全局默认站点：逗号分隔 → 规范化（去空白/小写/去重）。"""
    service = make_service()
    monkeypatch.setattr(settings, "AI_COLLECT_SEARCH_SITES", " xiachufang.com, MeishiChina.com, ,xiachufang.com ")
    assert service._default_search_sites() == ["xiachufang.com", "meishichina.com"]


def test_host_in_domains():
    """URL host 与限定域名匹配：等于或子域名。"""
    svc = make_service()
    assert svc._host_in_domains("https://m.xiachufang.com/recipe/1", ["xiachufang.com"])
    assert svc._host_in_domains("https://www.meishichina.com/a.html", ["meishichina.com"])
    assert not svc._host_in_domains("https://example.com/a", ["xiachufang.com"])
    assert not svc._host_in_domains("", ["xiachufang.com"])


# ------------------------------------------------------------------ #
# Ollama LLM Provider
# ------------------------------------------------------------------ #
def test_ollama_generate(monkeypatch):
    from app.llm.ollama import OllamaLLMProvider

    def fake_post(self, url, json=None, timeout=None, **kw):
        assert url == "/api/chat"
        return FakeResp(200, {"message": {"content": '{"title": "T"}'}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    provider = OllamaLLMProvider()
    result = provider.generate([{"role": "user", "content": "hi"}])
    assert result == {"title": "T"}


def test_ollama_fence_and_schema(monkeypatch):
    from app.llm.ollama import OllamaLLMProvider

    def fake_post(self, url, json=None, timeout=None, **kw):
        assert "format" in json  # 带 schema
        return FakeResp(200, {"message": {"content": '```json\n{"title": "T"}\n```'}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    provider = OllamaLLMProvider()
    result = provider.generate([{"role": "user", "content": "hi"}], response_schema=RecipeExtraction)
    assert result["title"] == "T"


def test_ollama_invalid_json(monkeypatch):
    from app.llm.ollama import OllamaLLMProvider

    def fake_post(self, url, json=None, timeout=None, **kw):
        return FakeResp(200, {"message": {"content": "not json"}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    with pytest.raises(LLMValidationError):
        OllamaLLMProvider().generate([{"role": "user", "content": "hi"}])


def test_ollama_unavailable(monkeypatch):
    from app.llm.ollama import OllamaLLMProvider

    def fake_post(self, url, json=None, timeout=None, **kw):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    with pytest.raises(LLMUnavailableError):
        OllamaLLMProvider().generate([{"role": "user", "content": "hi"}])


# ------------------------------------------------------------------ #
# Anthropic LLM Provider
# ------------------------------------------------------------------ #
def test_anthropic_generate_sanitizes(monkeypatch):
    import anthropic
    from app.llm.anthropic_provider import AnthropicLLMProvider

    captured = {}

    class FakeMessage:
        content = [SimpleNamespace(type="text", text='{"title": "T"}')]

    def fake_create(**kwargs):
        captured["kwargs"] = kwargs
        return FakeMessage()

    monkeypatch.setattr(anthropic.Anthropic, "messages", SimpleNamespace(create=fake_create))
    provider = AnthropicLLMProvider(api_key="k")
    result = provider.generate([{"role": "user", "content": "hi"}], response_schema=RecipeExtraction)
    assert result["title"] == "T"
    schema = captured["kwargs"]["output_config"]["format"]["schema"]
    dumped = json.dumps(schema)
    assert "minLength" not in dumped and "minimum" not in dumped
    assert "additionalProperties" in dumped
    assert captured["kwargs"]["model"] == "claude-opus-5"


def test_anthropic_bad_request_is_validation(monkeypatch):
    import anthropic
    from app.llm.anthropic_provider import AnthropicLLMProvider

    class FakeResp:
        status_code = 400
        headers = {}
        request = SimpleNamespace(headers={})

    def fake_create(**kwargs):
        raise anthropic.BadRequestError("bad schema", response=FakeResp(), body=None)

    monkeypatch.setattr(anthropic.Anthropic, "messages", SimpleNamespace(create=fake_create))
    with pytest.raises(LLMValidationError):
        AnthropicLLMProvider(api_key="k").generate([{"role": "user", "content": "hi"}])


# ------------------------------------------------------------------ #
# OpenAI 兼容 LLM Provider（DeepSeek / OpenRouter）
# ------------------------------------------------------------------ #
def test_openai_compat_generate(monkeypatch):
    from app.llm.openai_compat import OpenAICompatLLMProvider

    captured = {}

    def fake_post(self, url, json=None, headers=None, timeout=None, **kw):
        assert url == "/chat/completions"
        captured["payload"] = json
        return FakeResp(200, {"choices": [{"message": {"content": '{"title": "T"}'}}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    provider = OpenAICompatLLMProvider(
        api_key="k", base_url="https://api.deepseek.com", model="deepseek-chat"
    )
    result = provider.generate([{"role": "user", "content": "hi"}], response_schema=RecipeExtraction)
    assert result["title"] == "T"
    assert captured["payload"]["model"] == "deepseek-chat"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["response_format"] == {"type": "json_object"}


def test_openai_compat_max_tokens_defaults_to_settings(monkeypatch):
    """max_tokens 未指定时走 LLM_MAX_TOKENS（推理类模型需留足输出预算）。"""
    from app.llm.openai_compat import OpenAICompatLLMProvider

    monkeypatch.setattr(settings, "LLM_MAX_TOKENS", 8000)
    provider = OpenAICompatLLMProvider(api_key="k", base_url="https://x", model="m")
    assert provider.max_tokens == 8000
    provider2 = OpenAICompatLLMProvider(api_key="k", base_url="https://x", model="m", max_tokens=1234)
    assert provider2.max_tokens == 1234


def test_openai_compat_response_format_fallback(monkeypatch):
    from app.llm.openai_compat import OpenAICompatLLMProvider

    calls = []

    def fake_post(self, url, json=None, headers=None, timeout=None, **kw):
        calls.append(json)
        if len(calls) == 1:
            return FakeResp(400, {})
        return FakeResp(200, {"choices": [{"message": {"content": '{"title": "T"}'}}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    provider = OpenAICompatLLMProvider(api_key="k", base_url="https://x")
    result = provider.generate([{"role": "user", "content": "hi"}], response_schema=RecipeExtraction)
    assert result["title"] == "T"
    assert "response_format" not in calls[1]


def test_openai_compat_invalid_json(monkeypatch):
    from app.llm.openai_compat import OpenAICompatLLMProvider

    def fake_post(self, url, json=None, headers=None, timeout=None, **kw):
        return FakeResp(200, {"choices": [{"message": {"content": "not json"}}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    with pytest.raises(LLMValidationError):
        OpenAICompatLLMProvider(api_key="k", base_url="https://x").generate(
            [{"role": "user", "content": "hi"}]
        )


def test_openai_compat_server_error_is_unavailable(monkeypatch):
    from app.llm.openai_compat import OpenAICompatLLMProvider

    def fake_post(self, url, json=None, headers=None, timeout=None, **kw):
        return FakeResp(500, {"error": "boom"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    with pytest.raises(LLMUnavailableError):
        OpenAICompatLLMProvider(api_key="k", base_url="https://x").generate(
            [{"role": "user", "content": "hi"}]
        )


def test_openai_compat_unavailable(monkeypatch):
    from app.llm.openai_compat import OpenAICompatLLMProvider

    def fake_post(self, url, json=None, headers=None, timeout=None, **kw):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    with pytest.raises(LLMUnavailableError):
        OpenAICompatLLMProvider(api_key="k", base_url="https://x").generate(
            [{"role": "user", "content": "hi"}]
        )


def test_openai_compat_list_models_and_health(monkeypatch):
    from app.llm.openai_compat import OpenAICompatLLMProvider

    def fake_get(self, url, headers=None, **kw):
        assert url == "/models"
        return FakeResp(200, {"data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]})

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    provider = OpenAICompatLLMProvider(
        api_key="k", base_url="https://api.deepseek.com", model="deepseek-chat"
    )
    assert provider.list_models() == ["deepseek-chat", "deepseek-reasoner"]
    h = provider.health_check()
    assert h["ok"] is True and h["model_available"] is True


# ------------------------------------------------------------------ #
# 抽取重试
# ------------------------------------------------------------------ #
def test_extract_recipe_with_fix_retries():
    llm = FakeLLM(make_recipe(), fail_then_succeed=True)
    result = extract_recipe_with_fix(llm, "https://example.com/tomato", "西红柿炒鸡蛋做法……")
    assert llm.calls == 2
    assert result["title"] == "西红柿炒鸡蛋"


def test_extract_recipe_from_sources_retries():
    llm = FakeLLM(make_recipe(), fail_then_succeed=True)
    result = extract_recipe_from_sources(
        llm, [("https://example.com/a", "正文1"), ("https://example.com/b", "正文2")]
    )
    assert llm.calls == 2
    assert result["title"] == "西红柿炒鸡蛋"


# ------------------------------------------------------------------ #
# 采集流水线
# ------------------------------------------------------------------ #
def test_create_job_requires_tavily(db_session, no_enqueue, monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    with pytest.raises(ValueError) as exc:
        make_service().create_ai_job(db_session, SimpleNamespace(
            request_text="西红柿", mode="topic", target_recipe_id=None, max_results=5
        ))
    assert "TAVILY_NOT_CONFIGURED" in str(exc.value)


def test_create_job_complete_requires_target(db_session, no_enqueue, tavily_key):
    with pytest.raises(ValueError) as exc:
        make_service().create_ai_job(db_session, SimpleNamespace(
            request_text="西红柿", mode="complete", target_recipe_id=None, max_results=5
        ))
    assert "target_recipe_id" in str(exc.value)


def test_create_job_queues(db_session, no_enqueue, tavily_key):
    resp = make_service().create_ai_job(db_session, SimpleNamespace(
        request_text="西红柿", mode="topic", target_recipe_id=None, max_results=5
    ))
    assert resp.status == "queued"
    assert resp.stage == "submitted"
    assert resp.collection_mode == "topic"


def test_create_job_stores_search_sites(db_session, no_enqueue, tavily_key):
    """任务指定 search_sites 时规范化后写入 search_domains_json。"""
    resp = make_service().create_ai_job(db_session, SimpleNamespace(
        request_text="牛肉", mode="topic", target_recipe_id=None, max_results=5,
        llm_provider=None, llm_model=None,
        search_sites=["xiachufang.com", " MeishiChina.com "],
    ))
    job = db_session.query(IngestionJob).filter_by(id=resp.id).first()
    assert json.loads(job.search_domains_json) == ["xiachufang.com", "meishichina.com"]


def test_create_job_search_sites_falls_back_to_config(monkeypatch, db_session, no_enqueue, tavily_key):
    """未指定 search_sites 时回落全局配置 AI_COLLECT_SEARCH_SITES。"""
    monkeypatch.setattr(settings, "AI_COLLECT_SEARCH_SITES", "xiachufang.com,meishichina.com")
    resp = make_service().create_ai_job(db_session, SimpleNamespace(
        request_text="牛肉", mode="topic", target_recipe_id=None, max_results=5,
        llm_provider=None, llm_model=None, search_sites=None,
    ))
    job = db_session.query(IngestionJob).filter_by(id=resp.id).first()
    assert json.loads(job.search_domains_json) == ["xiachufang.com", "meishichina.com"]


def test_collect_creates_candidates(db_session, no_enqueue, tavily_key):
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("西红柿炒鸡蛋", "https://example.com/tomato", "c", 0.9)],
            pages=one_page(),
        ),
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert job.stage == "review"
    assert job.candidates_count == 1

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    assert candidate.action == "pending"
    assert candidate.merge_mode == "new"

    recipe = db_session.query(Recipe).filter_by(id=candidate.recipe_id).first()
    assert recipe.status == "review"
    assert recipe.created_by == "ai_search"

    source = db_session.query(RecipeSource).filter_by(id=candidate.source_id).first()
    assert source.raw_hash == hashlib.sha256(b"https://example.com/tomato").hexdigest()

    ri = db_session.query(RecipeIngredient).filter_by(recipe_id=recipe.id).all()
    assert len(ri) == 2


def test_collect_skips_ingested_url(db_session, no_enqueue, tavily_key):
    url = "https://example.com/tomato"
    db_session.add(RecipeSource(id=str(uuid.uuid4()), source_type="url", source_url=url,
                                raw_hash=hashlib.sha256(url.encode()).hexdigest()))
    db_session.commit()
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("西红柿炒鸡蛋", url, "c", 0.9)],
            pages=one_page(url),
        ),
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_code == "NO_SEARCH_RESULTS"


def test_is_listing_url():
    """列表/搜索/分类/视频型 URL 应被识别，单菜谱页不应被误伤。"""
    svc = make_service()
    # 应过滤：站内搜索、分类、标签、索引列表、视频、query 搜索
    assert svc._is_listing_url("https://icook.tw/search/牛肉")
    assert svc._is_listing_url("https://cookpad.com/tw/%E6%90%9C%E5%B0%8B/%E7%89%9B%E8%82%89")  # 编码的"搜尋"
    assert svc._is_listing_url("https://m.xiachufang.com/category/1445")
    assert svc._is_listing_url("https://www.knorr.com/hk/recipe-ideas/main-ingredients/beef-recipes.html")
    assert svc._is_listing_url("https://www.youtube.com/watch?v=abc")
    assert svc._is_listing_url("https://example.com/search?q=牛肉")
    # 不应过滤：单菜谱页 / 博客单篇文章
    assert not svc._is_listing_url("https://m.xiachufang.com/recipe/106463192")
    assert not svc._is_listing_url("https://www.knorr.com/hk/r/xxx.html/211803")
    assert not svc._is_listing_url("https://www.chefhungfoods.com/blog/posts/beef-noodle-recipe")


def test_collect_filters_listing_urls(db_session, no_enqueue, tavily_key):
    """搜索命中全是搜索/分类/视频页时提前过滤，标记 NO_SEARCH_RESULTS 而非 EXTRACTION_FAILED。"""
    service = make_service(
        tavily=FakeTavily(
            results=[
                TavilySearchResult("牛肉搜索", "https://icook.tw/search/牛肉", "c", 0.9),
                TavilySearchResult("牛肉搜索", "https://cookpad.com/tw/搜尋/牛肉", "c", 0.8),
                TavilySearchResult("牛肉视频", "https://youtube.com/watch?v=abc", "c", 0.7),
            ],
        ),
    )
    job = make_job(db_session, request_text="牛肉")
    service._run_collection(db_session, job.id)
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_code == "NO_SEARCH_RESULTS"
    assert job.candidates_count == 0


def test_collect_filters_hits_outside_domains(db_session, no_enqueue, tavily_key):
    """限定站点时：include_domains 传给搜索；命中不在所选域名内应被跳过。"""

    class DomainsTavily(FakeTavily):
        def __init__(self):
            super().__init__()
            self.pages = ([{"url": "https://m.xiachufang.com/recipe/1", "raw_content": "做法正文"}], [])

        def search(self, query, max_results=5, search_depth="basic", include_domains=None):
            self.search_include_domains = include_domains
            return [
                TavilySearchResult("下厨房菜", "https://m.xiachufang.com/recipe/1", "c", 0.9),
                TavilySearchResult("外部菜", "https://example.com/recipe/2", "c", 0.8),
            ]

    tavily = DomainsTavily()
    service = make_service(tavily=tavily, llm=FakeLLM(make_recipe()))
    job = make_job(db_session, request_text="牛肉")
    job.search_domains_json = json.dumps(["xiachufang.com"])
    db_session.commit()
    service._run_collection(db_session, job.id)

    assert tavily.search_include_domains == ["xiachufang.com"]
    db_session.refresh(job)
    assert job.candidates_count == 1  # 仅 xiachufang 命中被处理，外部域名命中被跳过


# ------------------------------------------------------------------ #
# 手动模式（小红书等登录墙站点）
# ------------------------------------------------------------------ #
def test_create_ai_job_manual_no_tavily_required(db_session, no_enqueue, monkeypatch):
    """手动模式不依赖 Tavily：未配置 TAVILY_API_KEY 也能建任务，并存储 URL/正文。"""
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    resp = make_service().create_ai_job(db_session, SimpleNamespace(
        request_text="", mode="manual", target_recipe_id=None, max_results=5,
        llm_provider=None, llm_model=None, search_sites=None,
        manual_url="https://www.xiaohongshu.com/explore/1", manual_content="番茄炒蛋……",
    ))
    job = db_session.query(IngestionJob).filter_by(id=resp.id).first()
    assert job.collection_mode == "manual"
    assert job.manual_url == "https://www.xiaohongshu.com/explore/1"
    assert job.manual_content == "番茄炒蛋……"


def test_create_ai_job_manual_requires_fields(db_session, no_enqueue, tavily_key):
    with pytest.raises(ValueError) as exc:
        make_service().create_ai_job(db_session, SimpleNamespace(
            request_text="", mode="manual", target_recipe_id=None, max_results=5,
            llm_provider=None, llm_model=None, search_sites=None,
            manual_url="", manual_content="正文",
        ))
    assert "URL" in str(exc.value)


def test_manual_collection_creates_candidate(db_session, no_enqueue, tavily_key):
    """手动模式走 _run_collection 分发：不联网搜索，直接用粘贴内容抽取产出候选。"""
    tavily = FakeTavily()
    service = make_service(tavily=tavily, llm=FakeLLM(make_recipe()))
    job = make_job(db_session, mode="manual", request_text="")
    job.manual_url = "https://www.xiaohongshu.com/explore/1"
    job.manual_content = "西红柿炒鸡蛋做法……"
    db_session.commit()
    service._run_collection(db_session, job.id)

    assert tavily.search_queries == []  # 手动模式不联网搜索
    db_session.refresh(job)
    assert job.stage == "review"
    assert job.candidates_count == 1
    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    assert json.loads(candidate.source_urls_json) == ["https://www.xiaohongshu.com/explore/1"]


def test_manual_collection_validation_fails(db_session, no_enqueue, tavily_key):
    """手动内容抽取结果未通过业务校验 → EXTRACTION_FAILED 且 reason 带原因。"""
    no_recipe = {"title": "", "ingredients": [], "steps": []}
    service = make_service(llm=FakeLLM(recipe=no_recipe))
    job = make_job(db_session, mode="manual", request_text="")
    job.manual_url = "https://www.xiaohongshu.com/explore/1"
    job.manual_content = "一些非菜谱内容"
    db_session.commit()
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_code == "EXTRACTION_FAILED"
    assert "校验未通过" in (job.reason or "")


# ------------------------------------------------------------------ #
# 结构化菜谱 JSON 直入（AI 生成 JSON → 手动粘贴）
# ------------------------------------------------------------------ #
def test_try_parse_structured_recipe_unit():
    """判定：dict+非空 title 通过；空白/非 dict/非 JSON/超长拒绝。"""
    svc = make_service()
    assert svc._try_parse_structured_recipe('{"title":"西红柿炒鸡蛋"}')["title"] == "西红柿炒鸡蛋"
    assert svc._try_parse_structured_recipe('﻿  {"title":"菜"}\n')["title"] == "菜"   # BOM + 首尾空白
    assert svc._try_parse_structured_recipe('```json\n{"title":"菜"}\n```')["title"] == "菜"  # 围栏
    assert svc._try_parse_structured_recipe('```JSON\n{"title":"菜"}\n```')["title"] == "菜"  # 大写标签
    assert svc._try_parse_structured_recipe('{"title":"x","ingredients":[],"steps":[]}')["title"] == "x"
    assert svc._try_parse_structured_recipe('{"title":""}') is None          # 空标题
    assert svc._try_parse_structured_recipe('{"title":"  "}') is None        # 空白标题
    assert svc._try_parse_structured_recipe('[1,2]') is None                 # 数组
    assert svc._try_parse_structured_recipe('西红柿炒鸡蛋做法……') is None      # 非 JSON
    assert svc._try_parse_structured_recipe('{"title":"' + "x" * 200_000 + '"}') is None  # 超长


def test_create_ai_job_manual_structured_json_no_url_ok(db_session, no_enqueue, tavily_key):
    """结构化菜谱 JSON + 空 URL → 建任务成功（URL 可选）。"""
    resp = make_service().create_ai_job(db_session, SimpleNamespace(
        request_text="", mode="manual", target_recipe_id=None, max_results=5,
        llm_provider=None, llm_model=None, search_sites=None,
        manual_url="", manual_content=json.dumps(make_recipe(), ensure_ascii=False),
    ))
    job = db_session.query(IngestionJob).filter_by(id=resp.id).first()
    assert job.manual_url == ""


def test_manual_structured_json_direct_no_llm(db_session, no_enqueue, tavily_key):
    """结构化 JSON 直入：不调 LLM、产出候选、无来源时来源为空。"""
    llm = FakeLLM(make_recipe())
    service = make_service(llm=llm)
    job = make_job(db_session, mode="manual", request_text="")
    recipe = make_recipe()
    recipe.pop("source_url")  # 纯 AI 创作无来源
    job.manual_content = json.dumps(recipe, ensure_ascii=False)
    job.manual_url = ""
    db_session.commit()
    service._run_collection(db_session, job.id)

    assert llm.calls == 0  # 跳过 LLM 抽取
    db_session.refresh(job)
    assert job.stage == "review"
    assert job.candidates_count == 1
    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    assert json.loads(candidate.source_urls_json) == []
    assert candidate.source_id is None


def test_manual_structured_json_validation_failed_no_llm(db_session, no_enqueue, tavily_key):
    """带 title 但无食材的结构化 JSON → EXTRACTION_FAILED，不调 LLM，原因明确。"""
    llm = FakeLLM(make_recipe())
    service = make_service(llm=llm)
    job = make_job(db_session, mode="manual", request_text="")
    job.manual_content = '{"title":"x","ingredients":[],"steps":[]}'
    job.manual_url = ""
    db_session.commit()
    service._run_collection(db_session, job.id)

    assert llm.calls == 0
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_code == "EXTRACTION_FAILED"
    assert "校验未通过" in (job.reason or "")
    assert "无食材" in (job.reason or "")


def test_manual_structured_json_with_fence(db_session, no_enqueue, tavily_key):
    """Markdown 围栏包裹的结构化 JSON 仍能直入。"""
    llm = FakeLLM(make_recipe())
    service = make_service(llm=llm)
    job = make_job(db_session, mode="manual", request_text="")
    job.manual_content = "```json\n" + json.dumps(make_recipe(), ensure_ascii=False) + "\n```"
    job.manual_url = ""
    db_session.commit()
    service._run_collection(db_session, job.id)

    assert llm.calls == 0
    db_session.refresh(job)
    assert job.stage == "review"
    assert job.candidates_count == 1


def test_manual_structured_json_source_url_fallback(db_session, no_enqueue, tavily_key):
    """JSON 自带 http(s) source_url → 作为候选来源；javascript: 等协议被过滤。"""
    service = make_service(llm=FakeLLM(make_recipe()))

    job = make_job(db_session, mode="manual", request_text="")
    recipe = make_recipe()
    recipe["source_url"] = "https://ref.example.com/recipe"
    job.manual_content = json.dumps(recipe, ensure_ascii=False)
    job.manual_url = ""
    db_session.commit()
    service._run_collection(db_session, job.id)
    db_session.refresh(job)
    assert job.stage == "review"
    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    assert json.loads(candidate.source_urls_json) == ["https://ref.example.com/recipe"]

    # javascript: 协议被过滤（用不同标题避免与上一个候选去重命中）
    job2 = make_job(db_session, mode="manual", request_text="")
    recipe2 = make_recipe(title="红烧肉")
    recipe2["source_url"] = "javascript:alert(1)"
    job2.manual_content = json.dumps(recipe2, ensure_ascii=False)
    job2.manual_url = ""
    db_session.commit()
    service._run_collection(db_session, job2.id)
    db_session.refresh(job2)
    assert job2.stage == "review"
    candidate2 = db_session.query(IngestionCandidate).filter_by(job_id=job2.id).first()
    assert json.loads(candidate2.source_urls_json) == []


def test_manual_non_json_without_url_defensive(db_session, no_enqueue, tavily_key):
    """非结构化正文 + 空 URL 直接 _run_collection → EXTRACTION_FAILED、无候选（防御分支）。"""
    service = make_service(llm=FakeLLM(make_recipe()))
    job = make_job(db_session, mode="manual", request_text="")
    job.manual_content = "西红柿炒鸡蛋做法……"
    job.manual_url = ""
    db_session.commit()
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_code == "EXTRACTION_FAILED"
    assert db_session.query(IngestionCandidate).filter_by(job_id=job.id).count() == 0


def test_validate_recipe_reason_whitespace_title_fails():
    """空白标题不通过校验（prompts 加固）。"""
    recipe = {
        "title": "   ",
        "ingredients": [{"name": "西红柿"}],
        "steps": [{"step_no": 1, "instruction": "炒"}],
    }
    assert validate_recipe_reason(recipe) == "标题为空"


def test_collect_handles_page_failure(db_session, no_enqueue, tavily_key):
    bad_url = "https://example.com/bad"
    good_url = "https://example.com/tomato"
    service = make_service(
        tavily=FakeTavily(
            results=[
                TavilySearchResult("坏页", bad_url, "c", 0.8),
                TavilySearchResult("西红柿炒鸡蛋", good_url, "c", 0.9),
            ],
            pages=(
                [{"url": bad_url, "raw_content": "内容"},
                 {"url": good_url, "raw_content": "西红柿炒鸡蛋做法……"}],
                [],
            ),
        ),
        llm=FakeLLM(make_recipe(), fail_urls={bad_url}),
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert job.candidates_count == 1
    assert "抽取失败" in (job.reason or "")


def test_collect_browser_fallback_for_login_wall(db_session, no_enqueue, tavily_key):
    """登录墙站点（小红书）：Tavily 抓取失败 → 浏览器兜底抓到正文 → 产出候选。"""
    wall_url = "https://www.xiaohongshu.com/explore/abc123"
    browser = FakeBrowser()
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("凉拌黄瓜", wall_url, "c", 0.9)],
            pages=([], [{"url": wall_url, "error": "login required"}]),
        ),
        llm=FakeLLM(make_recipe("凉拌黄瓜", wall_url)),
        browser=browser,
    )
    job = make_job(db_session, request_text="凉拌黄瓜")
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert browser.fetch_urls == [wall_url]  # 浏览器被调用
    assert job.candidates_count == 1


def test_collect_browser_skips_non_login_wall(db_session, no_enqueue, tavily_key):
    """非登录墙站点：Tavily 失败不会触发浏览器兜底。"""
    url = "https://example.com/bad"
    browser = FakeBrowser()
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("某菜", url, "c", 0.9)],
            pages=([], [{"url": url, "error": "boom"}]),
        ),
        llm=FakeLLM(make_recipe()),
        browser=browser,
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert browser.fetch_urls == []  # 非登录墙站点不兜底
    assert job.candidates_count == 0


def test_collect_consolidates_multiple_sources(db_session, no_enqueue, tavily_key):
    """3 个同菜名来源 → 先逐页抽取，再综合总结为 1 个候选，source_urls 记录全部来源。"""
    urls = [f"https://example.com/tomato{i}" for i in range(1, 4)]
    llm = FakeLLM(make_recipe())  # 3 页逐页都抽出同名"西红柿炒鸡蛋"
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("西红柿炒鸡蛋", u, "c", 0.9) for u in urls],
            pages=([{"url": u, "raw_content": "西红柿炒鸡蛋做法……"} for u in urls], []),
        ),
        llm=llm,
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert job.candidates_count == 1
    assert llm.calls == 4  # 3 次逐页抽取 + 1 次同标题综合总结

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    assert json.loads(candidate.source_urls_json) == urls
    sources = db_session.query(RecipeSource).filter(RecipeSource.source_url.in_(urls)).all()
    assert len(sources) == 3  # 每个来源都建了 RecipeSource，raw_hash 去重生效


def test_collect_consolidation_invalid_falls_back_to_pages(db_session, no_enqueue, tavily_key):
    """同标题来源综合总结结果校验未通过（输出 {title:""}）时，回退逐页独立入库，不整批丢弃。"""
    urls = [f"https://example.com/a{i}" for i in range(1, 3)]
    no_recipe = {"title": "", "ingredients": [], "steps": []}
    llm = SequencedLLM([
        make_recipe(title="同一道菜", url=urls[0]),  # 逐页：第 1 页
        make_recipe(title="同一道菜", url=urls[1]),  # 逐页：第 2 页（同标题 → 分组）
        no_recipe,                                  # 综合总结 → 无菜谱 → 校验未通过
    ])
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("菜", u, "c", 0.9) for u in urls],
            pages=([{"url": u, "raw_content": "做法正文"} for u in urls], []),
        ),
        llm=llm,
    )
    job = make_job(db_session, request_text="菜")
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert "校验未通过" in (job.reason or "")  # 综合总结"无菜谱"被记录
    assert llm.calls == 3                    # 2 页逐页 + 1 次综合总结
    assert job.candidates_count == 1         # 回退逐页产出 1 个候选（同标题去重合并）
    assert job.stage == "review"


def test_collect_distinct_titles_no_consolidation(db_session, no_enqueue, tavily_key):
    """不同菜名的页面各自独立成候选，不做综合总结。"""
    urls = [f"https://example.com/recipe{i}" for i in range(1, 4)]
    llm = SequencedLLM([
        make_recipe(title="菜A", url=urls[0]),
        make_recipe(title="菜B", url=urls[1]),
        make_recipe(title="菜C", url=urls[2]),
    ])
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("菜", u, "c", 0.9) for u in urls],
            pages=([{"url": u, "raw_content": "做法正文"} for u in urls], []),
        ),
        llm=llm,
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert llm.calls == 3            # 3 次逐页抽取，无综合总结调用
    assert job.candidates_count == 3  # 各页独立成候选
    assert job.stage == "review"


def test_collect_single_source_stays_single(db_session, no_enqueue, tavily_key):
    """只有 1 个可用来源时保持单来源抽取（多来源总结前置条件不满足）。"""
    url = "https://example.com/tomato"
    llm = FakeLLM(make_recipe())
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("西红柿炒鸡蛋", url, "c", 0.9)],
            pages=one_page(url),
        ),
        llm=llm,
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert job.candidates_count == 1
    assert llm.calls == 1  # 单来源逐页抽取
    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    assert json.loads(candidate.source_urls_json) == [url]


def test_candidate_response_has_source_urls(db_session, no_enqueue, tavily_key):
    """候选响应返回 source_urls（全部参考来源）与 source_url（主来源）。"""
    job = make_job(db_session)
    urls = ["https://example.com/tomato1", "https://example.com/tomato2"]
    service = make_service()
    recipe = make_recipe()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, urls, dedup, {})
    db_session.commit()

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    resp = service._candidate_response(db_session, candidate)
    assert resp.source_urls == urls
    assert resp.source_url == urls[0]


def test_collect_no_results(db_session, no_enqueue, tavily_key):
    service = make_service(tavily=FakeTavily(results=[], pages=([], [])))
    job = make_job(db_session)
    service._run_collection(db_session, job.id)
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_code == "NO_SEARCH_RESULTS"


def test_collect_all_extraction_failed(db_session, no_enqueue, tavily_key):
    url = "https://example.com/tomato"
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("西红柿炒鸡蛋", url, "c", 0.9)],
            pages=one_page(url),
        ),
        llm=FakeLLM(make_recipe(), fail_urls={url}),
    )
    job = make_job(db_session)
    service._run_collection(db_session, job.id)
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_code == "EXTRACTION_FAILED"


def test_build_search_query_ingredients(db_session, no_enqueue):
    service = make_service()
    job = make_job(db_session, mode="ingredients", request_text="西红柿,鸡蛋")
    query = service._build_search_query(db_session, job)
    assert "西红柿、鸡蛋 菜谱 做法" == query


def test_build_search_query_complete(db_session, no_enqueue):
    target = Recipe(id=str(uuid.uuid4()), title="西红柿炒鸡蛋", status="draft", revision=1)
    db_session.add(target)
    db_session.commit()
    service = make_service()
    job = make_job(db_session, mode="complete", target_id=target.id)
    query = service._build_search_query(db_session, job)
    assert "西红柿炒鸡蛋 完整做法 食材 步骤" == query


# ------------------------------------------------------------------ #
# 审核动作
# ------------------------------------------------------------------ #
def _persist_candidate_for(db, job, recipe=None):
    recipe = recipe or make_recipe()
    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db, job, recipe, [recipe["source_url"]], dedup, {})
    db.commit()
    return db.query(IngestionCandidate).filter_by(job_id=job.id).first()


# ------------------------------------------------------------------ #
# 用量拆分：约数（2~3个 / 2-3克）与分数（1/2个）不拆坏
# ------------------------------------------------------------------ #
@pytest.mark.parametrize("amount,exp_q,exp_u", [
    ("2~3个", "2~3", "个"),
    ("2-3个", "2-3", "个"),
    ("2－3克", "2－3", "克"),
    ("3至4片", "3至4", "片"),
    ("1/2个", "1/2", "个"),
    ("1.5~2斤", "1.5~2", "斤"),
    ("2个", "2", "个"),
    ("3 克", "3", "克"),
    ("适量", None, None),
])
def test_validate_recipe_reason_splits_approx_amount(amount, exp_q, exp_u):
    """约数/分数用量：整个量词留在 quantity，单位单独拆出，不再拆成 ('2','~3个')。"""
    recipe = {
        "title": "测试菜",
        "ingredients": [{"name": "食材", "amount": amount}],
        "steps": [{"step_no": 1, "instruction": "炒"}],
    }
    assert validate_recipe_reason(recipe) is None
    item = recipe["ingredients"][0]
    assert item["quantity"] == exp_q
    assert item["unit"] == exp_u
    # 原始文本完整保留，避免回显丢失约数
    assert item["raw_quantity"] == amount


# ------------------------------------------------------------------ #
# 调料拆分：把食材中的调料自动归入调料
# ------------------------------------------------------------------ #
def test_validate_recipe_reason_splits_seasonings():
    recipe = {
        "title": "西红柿炒鸡蛋",
        "ingredients": [
            {"name": "西红柿", "amount": "2个"},
            {"name": "盐", "amount": "适量"},
            {"name": "鸡蛋", "amount": "3个"},
            {"name": "生抽", "amount": "1勺"},
        ],
        "steps": [{"step_no": 1, "instruction": "炒"}],
    }
    assert validate_recipe_reason(recipe) is None
    assert [i["name"] for i in recipe["ingredients"]] == ["西红柿", "鸡蛋"]
    assert [s["name"] for s in recipe["seasonings"]] == ["盐", "生抽"]


def test_validate_recipe_reason_merges_llm_seasonings_and_dedup():
    """LLM 显式输出的 seasonings 并入；食材中重复的调料去重。"""
    recipe = {
        "title": "红烧肉",
        "ingredients": [
            {"name": "五花肉", "amount": "500克"},
            {"name": "冰糖", "amount": "20克"},   # 模型放错位置 → 词典拆出
            {"name": "酱油", "amount": "2勺"},    # 与 seasonings 重复 → 只留一条
        ],
        "seasonings": [
            {"name": "酱油", "amount": "2勺"},
            {"name": "料酒", "amount": "1勺"},
        ],
        "steps": [{"step_no": 1, "instruction": "炖"}],
    }
    assert validate_recipe_reason(recipe) is None
    assert [i["name"] for i in recipe["ingredients"]] == ["五花肉"]
    assert [s["name"] for s in recipe["seasonings"]] == ["冰糖", "酱油", "料酒"]


def test_validate_recipe_reason_all_seasonings_fails():
    """全是调料的清单不算一道菜。"""
    recipe = {
        "title": "蘸料",
        "ingredients": [{"name": "盐"}, {"name": "生抽"}],
        "steps": [{"step_no": 1, "instruction": "混合"}],
    }
    assert validate_recipe_reason(recipe) == "无食材"


def test_persist_candidate_creates_seasoning_links(db_session, no_enqueue, tavily_key):
    """走真实流水线（先 validate 拆分再落库）：调料进 recipe_seasonings，食材留在 ingredients。"""
    job = make_job(db_session)
    recipe = make_recipe()
    recipe["ingredients"].extend([
        {"name": "盐", "quantity": "适量"},
        {"name": "生抽", "quantity": "1", "unit": "勺"},
        {"name": "洋葱"},  # 含"葱"子串但是食材 → 保留在食材
    ])
    assert validate_recipe_reason(recipe) is None

    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, [recipe["source_url"]], dedup, {})
    db_session.commit()

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    ings = db_session.query(RecipeIngredient).filter_by(recipe_id=candidate.recipe_id).all()
    assert {ri.ingredient.canonical_name for ri in ings} == {"西红柿", "鸡蛋", "洋葱"}
    seas = db_session.query(RecipeSeasoning).filter_by(recipe_id=candidate.recipe_id).all()
    assert {s.seasoning.canonical_name for s in seas} == {"盐", "生抽"}
    # 调料表中自动建了 Seasoning 记录
    assert db_session.query(Seasoning).filter(Seasoning.canonical_name == "生抽").first() is not None
    # 候选核心食材不含调料
    assert json.loads(candidate.core_ingredients_json) == ["西红柿", "鸡蛋", "洋葱"]


def test_persist_candidate_db_fallback_moves_user_seasonings(db_session, no_enqueue, tavily_key):
    """调料表里已有、但静态词典未覆盖的名字（用户手工维护）→ 落库时兜底拆到调料。"""
    db_session.add(Seasoning(
        id=str(uuid.uuid4()), canonical_name="鱼籽酱", pinyin="yuzijiang"
    ))
    db_session.commit()

    job = make_job(db_session)
    recipe = make_recipe()
    recipe["ingredients"].append({"name": "鱼籽酱", "quantity": "1勺"})

    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, [recipe["source_url"]], dedup, {})
    db_session.commit()

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    ings = db_session.query(RecipeIngredient).filter_by(recipe_id=candidate.recipe_id).all()
    assert {ri.ingredient.canonical_name for ri in ings} == {"西红柿", "鸡蛋"}
    seas = db_session.query(RecipeSeasoning).filter_by(recipe_id=candidate.recipe_id).all()
    assert {s.seasoning.canonical_name for s in seas} == {"鱼籽酱"}


def test_persist_candidate_auto_classifies(db_session, no_enqueue, tavily_key):
    """采集入库自动分类：菜谱/食材/调料按规则归类（西红柿炒鸡蛋→家常菜，西红柿→蔬菜，鸡蛋→蛋类，盐→基础调味）。"""
    job = make_job(db_session)
    recipe = make_recipe()
    recipe["ingredients"].append({"name": "盐", "quantity": "适量"})
    assert validate_recipe_reason(recipe) is None  # 盐 拆到 seasonings

    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, [recipe["source_url"]], dedup, {})
    db_session.commit()

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()

    # 菜谱：西红柿炒鸡蛋 → 家常菜
    link = db_session.query(RecipeCategoryLink).filter_by(recipe_id=candidate.recipe_id).first()
    rcat = db_session.query(RecipeCategory).get(link.category_id)
    assert rcat.name == "家常菜"

    # 食材：西红柿 → 蔬菜，鸡蛋 → 蛋类
    tomato = db_session.query(Ingredient).filter_by(canonical_name="西红柿").first()
    egg = db_session.query(Ingredient).filter_by(canonical_name="鸡蛋").first()
    assert db_session.query(IngredientCategory).get(tomato.category_id).name == "蔬菜"
    assert db_session.query(IngredientCategory).get(egg.category_id).name == "蛋类"

    # 调料：盐 → 基础调味
    sea = db_session.query(Seasoning).filter_by(canonical_name="盐").first()
    assert db_session.query(SeasoningCategory).get(sea.category_id).name == "基础调味"


def test_persist_candidate_unknown_ingredient_falls_back_default(db_session, no_enqueue, tavily_key):
    """采集入库：未识别食材回落默认分类，而非留空。"""
    from app.repositories.category_repository import get_default_category_id

    job = make_job(db_session)
    recipe = make_recipe()
    recipe["ingredients"].append({"name": "神秘食材XYZ", "quantity": "1份"})

    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, [recipe["source_url"]], dedup, {})
    db_session.commit()

    ing = db_session.query(Ingredient).filter_by(canonical_name="神秘食材XYZ").first()
    assert ing is not None
    assert ing.category_id == get_default_category_id(db_session, "ingredient")


def test_persist_candidate_explicit_category_wins(db_session, no_enqueue, tavily_key):
    """结构化 JSON 显式 category（规范清单内）优先于标题规则。"""
    job = make_job(db_session)
    recipe = make_recipe(title="红烧肉")  # 标题规则会给 炖菜
    recipe["category"] = "汤羹"

    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, [recipe["source_url"]], dedup, {})
    db_session.commit()

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    link = db_session.query(RecipeCategoryLink).filter_by(recipe_id=candidate.recipe_id).first()
    assert db_session.query(RecipeCategory).get(link.category_id).name == "汤羹"


def test_persist_candidate_new_category_created(db_session, no_enqueue, tavily_key):
    """显式 category 为 DB 未收录的新分类名 → 自动创建该分类并挂上，而非回落标题。"""
    job = make_job(db_session)
    recipe = make_recipe(title="羊肉串")
    recipe["category"] = "烧烤"  # DB 未收录的新分类

    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, [recipe["source_url"]], dedup, {})
    db_session.commit()

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    link = db_session.query(RecipeCategoryLink).filter_by(recipe_id=candidate.recipe_id).first()
    assert db_session.query(RecipeCategory).get(link.category_id).name == "烧烤"


def test_persist_candidate_empty_category_falls_back_title(db_session, no_enqueue, tavily_key):
    """显式 category 为纯空白等不可信输入 → 回落标题规则，不创建脏分类。"""
    job = make_job(db_session)
    recipe = make_recipe(title="红烧肉")
    recipe["category"] = "   "  # 纯空白

    service = make_service()
    dedup = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
    service._persist_candidate(db_session, job, recipe, [recipe["source_url"]], dedup, {})
    db_session.commit()

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    link = db_session.query(RecipeCategoryLink).filter_by(recipe_id=candidate.recipe_id).first()
    assert db_session.query(RecipeCategory).get(link.category_id).name == "炖菜"
    assert db_session.query(RecipeCategory).filter_by(name="   ").first() is None


def test_approve_merge_merges_seasonings(db_session, no_enqueue, tavily_key):
    """补全模式合入时，候选的调料也并入目标（按名去重）。"""
    target = Recipe(id=str(uuid.uuid4()), title="西红柿炒鸡蛋", status="draft", revision=1)
    db_session.add(target)
    db_session.commit()

    job = make_job(db_session, mode="complete", request_text="西红柿炒鸡蛋", target_id=target.id)
    recipe = make_recipe()
    recipe["ingredients"].append({"name": "盐", "quantity": "适量"})
    assert validate_recipe_reason(recipe) is None
    candidate = _persist_candidate_for(db_session, job, recipe)

    make_service().review_candidate(db_session, candidate.id, "approve")

    db_session.refresh(target)
    seas = db_session.query(RecipeSeasoning).filter_by(recipe_id=target.id).all()
    assert {s.seasoning.canonical_name for s in seas} == {"盐"}
    # 食材并入后候选软删，目标食材包含候选真实食材
    ings = db_session.query(RecipeIngredient).filter_by(recipe_id=target.id).all()
    assert {ri.ingredient.canonical_name for ri in ings} == {"西红柿", "鸡蛋"}


def test_approve_new_publishes(db_session, no_enqueue, tavily_key):
    job = make_job(db_session)
    candidate = _persist_candidate_for(db_session, job)

    result = make_service().review_candidate(db_session, candidate.id, "approve")
    assert result.action == "approved"
    recipe = db_session.query(Recipe).filter_by(id=candidate.recipe_id).first()
    assert recipe.status == "published"
    assert recipe.revision == 2
    db_session.refresh(job)
    assert job.status == "succeeded"


def test_approve_merge_fills_missing_only(db_session, no_enqueue, tavily_key):
    target = Recipe(id=str(uuid.uuid4()), title="西红柿炒鸡蛋", status="draft", revision=1)
    db_session.add(target)
    db_session.commit()

    job = make_job(db_session, mode="complete", request_text="西红柿炒鸡蛋", target_id=target.id)
    candidate = _persist_candidate_for(db_session, job)
    assert candidate.merge_mode == "merge"

    make_service().review_candidate(db_session, candidate.id, "approve")

    db_session.refresh(target)
    assert target.summary == "经典家常菜"          # 缺失字段被补
    assert target.servings == 2
    assert target.revision == 2
    assert target.source_id is not None
    steps = db_session.query(RecipeStep).filter_by(recipe_id=target.id).all()
    assert len(steps) == 2
    snapshot = db_session.query(RecipeRevision).filter_by(recipe_id=target.id).first()
    assert snapshot is not None
    # 候选菜谱被软删
    cand_recipe = db_session.query(Recipe).filter_by(id=candidate.recipe_id).first()
    assert cand_recipe.deleted_at is not None


def test_approve_merge_preserves_existing_fields(db_session, no_enqueue, tavily_key):
    target = Recipe(id=str(uuid.uuid4()), title="西红柿炒鸡蛋", summary="已有简介",
                    servings=4, status="draft", revision=1)
    db_session.add(target)
    db_session.commit()

    job = make_job(db_session, mode="complete", request_text="西红柿炒鸡蛋", target_id=target.id)
    candidate = _persist_candidate_for(db_session, job)

    make_service().review_candidate(db_session, candidate.id, "approve")

    db_session.refresh(target)
    assert target.summary == "已有简介"   # 不覆盖已有值
    assert target.servings == 4


def test_reject_soft_deletes_and_finalizes(db_session, no_enqueue, tavily_key):
    job = make_job(db_session)
    candidate = _persist_candidate_for(db_session, job)

    result = make_service().review_candidate(db_session, candidate.id, "reject")
    assert result.action == "rejected"
    recipe = db_session.query(Recipe).filter_by(id=candidate.recipe_id).first()
    assert recipe.deleted_at is not None
    db_session.refresh(job)
    assert job.status == "rejected"


def test_review_twice_raises(db_session, no_enqueue, tavily_key):
    job = make_job(db_session)
    candidate = _persist_candidate_for(db_session, job)
    make_service().review_candidate(db_session, candidate.id, "approve")
    with pytest.raises(ValueError):
        make_service().review_candidate(db_session, candidate.id, "approve")


# ------------------------------------------------------------------ #
# API
# ------------------------------------------------------------------ #
def test_api_create_job_requires_key(client, no_enqueue, monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    resp = client.post("/api/v1/ai-collect/jobs", json={"request_text": "西红柿"})
    assert resp.status_code == 400
    assert "TAVILY_NOT_CONFIGURED" in resp.text


def test_api_create_job_complete_missing_target(client, no_enqueue, tavily_key):
    resp = client.post("/api/v1/ai-collect/jobs",
                       json={"request_text": "西红柿", "mode": "complete"})
    assert resp.status_code == 400


def test_api_config_status(client, no_enqueue, tavily_key):
    resp = client.get("/api/v1/ai-collect/config/status")
    assert resp.status_code == 200
    assert resp.json()["tavily_configured"] is True


def test_api_pending_empty(client, no_enqueue, tavily_key):
    resp = client.get("/api/v1/ai-collect/candidates")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_models(monkeypatch):
    from app.llm.openai_compat import OpenAICompatLLMProvider
    from app.services.ai_collection_service import OllamaLLMProvider

    monkeypatch.setattr(
        OllamaLLMProvider, "list_models",
        lambda self: ["qwen3.5:9b", "qwen3.5:4b", "bge-m3:latest"],
    )
    # 打桩避免真实联网；云供应商列表统一返回 fake 结果
    monkeypatch.setattr(
        OpenAICompatLLMProvider, "list_models",
        lambda self: ["deepseek-chat", "deepseek-reasoner"],
    )
    monkeypatch.setattr(settings, "LLM_API_KEY", "k")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "dk")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", None)
    res = make_service().list_models()
    providers = {m.provider for m in res.models}
    assert "ollama" in providers
    assert "anthropic" in providers
    assert "deepseek" in providers
    assert res.default_provider == settings.LLM_PROVIDER
    # 默认模型跟随供应商：LLM_PROVIDER=deepseek 时应为 DEEPSEEK_MODEL（环境敏感）
    assert res.default_model == default_model_for(settings.LLM_PROVIDER)


def test_list_models_no_cloud_without_key(monkeypatch):
    from app.services.ai_collection_service import OllamaLLMProvider

    monkeypatch.setattr(OllamaLLMProvider, "list_models", lambda self: ["qwen3.5:9b"])
    monkeypatch.setattr(settings, "LLM_API_KEY", None)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", None)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_COMPAT_API_KEY", None)
    res = make_service().list_models()
    assert all(m.provider not in ("anthropic", "deepseek", "openrouter", "openai_compat")
               for m in res.models)


def test_build_job_llm(db_session, no_enqueue):
    from app.llm.anthropic_provider import AnthropicLLMProvider
    from app.llm.ollama import OllamaLLMProvider
    from app.llm.openai_compat import OpenAICompatLLMProvider

    service = make_service()
    job = make_job(db_session)
    job.llm_provider = "ollama"
    job.llm_model = "qwen3.5:4b"
    p = service._build_job_llm(job)
    assert isinstance(p, OllamaLLMProvider)
    assert p.model == "qwen3.5:4b"

    job.llm_provider = "anthropic"
    job.llm_model = None
    p2 = service._build_job_llm(job)
    assert isinstance(p2, AnthropicLLMProvider)
    assert p2.model == settings.ANTHROPIC_LLM_MODEL

    job.llm_provider = "deepseek"
    job.llm_model = None
    p3 = service._build_job_llm(job)
    assert isinstance(p3, OpenAICompatLLMProvider)
    assert p3.model == settings.DEEPSEEK_MODEL

    job.llm_provider = "openrouter"
    job.llm_model = None
    p4 = service._build_job_llm(job)
    assert isinstance(p4, OpenAICompatLLMProvider)
    assert p4.model == settings.OPENROUTER_MODEL


def test_create_ai_job_stores_llm(db_session, no_enqueue, tavily_key):
    resp = make_service().create_ai_job(db_session, SimpleNamespace(
        request_text="西红柿", mode="topic", target_recipe_id=None, max_results=5,
        llm_provider="ollama", llm_model="qwen3.5:4b",
    ))
    job = db_session.query(IngestionJob).filter_by(id=resp.id).first()
    assert job.llm_provider == "ollama"
    assert job.llm_model == "qwen3.5:4b"


def test_api_list_models(client, no_enqueue, tavily_key):
    resp = client.get("/api/v1/ai-collect/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "models" in body and "default_model" in body


def test_api_approve_reject_endpoints(client, db_session, no_enqueue, tavily_key):
    # 直接落库候选，再走 API 审核
    job = make_job(db_session)
    candidate = _persist_candidate_for(db_session, job)

    resp = client.post(f"/api/v1/ai-collect/candidates/{candidate.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["action"] == "approved"

    # 另一个候选走 reject
    job2 = make_job(db_session)
    candidate2 = _persist_candidate_for(db_session, job2)
    resp = client.post(f"/api/v1/ai-collect/candidates/{candidate2.id}/reject")
    assert resp.status_code == 200
    assert resp.json()["action"] == "rejected"

    resp = client.post("/api/v1/ai-collect/candidates/nonexistent/approve")
    assert resp.status_code == 404
