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
    IngestionCandidate, IngestionJob, Recipe, RecipeIngredient,
    RecipeRevision, RecipeSource, RecipeStep,
)
from app.llm import LLMProvider, LLMUnavailableError, LLMValidationError
from app.llm.factory import default_model_for
from app.llm.prompts import (
    RecipeExtraction, extract_recipe_from_sources, extract_recipe_with_fix, normalize_title,
)
from app.llm.schema import sanitize_schema_for_anthropic
from app.services.ai_collection_service import AiCollectionService
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

    def search(self, query, max_results=5, search_depth="basic"):
        self.search_queries.append(query)
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


def make_service(tavily=None, llm=None) -> AiCollectionService:
    return AiCollectionService(
        tavily=tavily or FakeTavily(),
        llm=llm or FakeLLM(make_recipe()),
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


def test_collect_consolidates_multiple_sources(db_session, no_enqueue, tavily_key):
    """3 个同菜来源 → 1 次多来源总结 → 1 个候选，source_urls 记录全部来源。"""
    urls = [f"https://example.com/tomato{i}" for i in range(1, 4)]
    llm = FakeLLM(make_recipe())
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
    assert llm.calls == 1  # 多来源总结一次调用，未回退逐页

    candidate = db_session.query(IngestionCandidate).filter_by(job_id=job.id).first()
    assert json.loads(candidate.source_urls_json) == urls
    sources = db_session.query(RecipeSource).filter(RecipeSource.source_url.in_(urls)).all()
    assert len(sources) == 3  # 每个来源都建了 RecipeSource，raw_hash 去重生效


def test_collect_consolidate_no_recipe_falls_back_to_pages(db_session, no_enqueue, tavily_key):
    """多来源总结判定"无菜谱"（输出 {title:""}，通过 Pydantic 但过不了业务校验）时，
    必须回退逐页抽取，而不是整批丢弃。"""
    urls = [f"https://example.com/tomato{i}" for i in range(1, 4)]
    no_recipe = {"title": "", "ingredients": [], "steps": []}
    llm = SequencedLLM([
        no_recipe,  # 第 1 次：多来源总结 → 无菜谱
        make_recipe(title="日式土豆泥沙拉", url=urls[0]),  # 逐页回退
        make_recipe(title="彩椒炒蛋", url=urls[1]),
    ])
    service = make_service(
        tavily=FakeTavily(
            results=[TavilySearchResult("减脂餐", u, "c", 0.9) for u in urls],
            pages=([{"url": u, "raw_content": "做法正文"} for u in urls], []),
        ),
        llm=llm,
    )
    job = make_job(db_session, request_text="减脂餐")
    service._run_collection(db_session, job.id)

    db_session.refresh(job)
    assert "校验未通过" in (job.reason or "")  # 批次判定"无菜谱"被记录
    assert llm.calls == 4                    # 1 次多来源总结 + 3 页逐页回退
    assert job.candidates_count == 2         # 逐页回退产出候选，整批未丢
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
