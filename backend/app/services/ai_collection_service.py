"""AI 联网采集菜谱入库业务逻辑层。

三种模式（topic/ingredients/complete）统一流水线：
提交任务 → 后台 Tavily 搜索 → 过滤已采集 URL → 抓取正文 → LLM 结构化抽取
（校验 + 一次修复重试）→ 去重判定 → 落库为 Recipe(status='review') 候选
+ IngestionCandidate(action='pending') → 人工审核（确认 new=发布、确认 merge=合入目标、拒绝=软删）。

后台任务用独立 DB session（get_db_context），绝不复用请求期 session。
"""
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import unquote, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.category_classifier import (
    classify_ingredient, classify_seasoning, resolve_recipe_category,
)
from app.core.config import settings
from app.core.pinyin import to_pinyin
from app.db.database import get_db_context
from app.db.models import (
    IngestionCandidate, IngestionJob, Ingredient, Recipe,
    RecipeCategoryLink, RecipeIngredient, RecipeRevision, RecipeSeasoning,
    RecipeSource, RecipeStep, RecipeTag, Seasoning, Tag,
)
from app.llm import (
    LLMProvider, LLMUnavailableError, LLMValidationError,
    build_llm_provider, default_model_for, get_llm_provider,
)
from app.llm.ollama import OllamaLLMProvider
from app.llm.openai_compat import OpenAICompatLLMProvider
from app.llm.prompts import (
    extract_recipe_from_sources, extract_recipe_with_fix,
    normalize_title, validate_recipe_reason,
)
from app.repositories.ai_collection_repository import AICollectionRepository
from app.repositories.category_repository import resolve_category_id
from app.repositories.ingredient_repository import IngredientRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.seasoning_repository import SeasoningRepository
from app.schemas.ai_collection import (
    AICollectionCreate, AICollectionJobResponse, CandidateResponse,
    ConfigStatusResponse, LLMModelOption, LLMModelsResponse,
    PaginatedCandidateResponse,
)
from app.services.browser_fetcher import BrowserFetchError, BrowserFetcher
from app.services.tavily_client import TavilyClient, TavilyUnavailableError, clean_page_text
from app.tasks import executor

logger = logging.getLogger(__name__)

# 结构化菜谱 JSON 直入的上限：超过则放弃直入、回退 LLM 截断路径
# （LLM 路径经 build_extraction_messages 截断到 AI_COLLECT_PAGE_CHARS），
# 防止恶意/病态超大粘贴拖慢 json.loads。
_MAX_STRUCTURED_JSON_CHARS = 200_000


class AiCollectionService:
    """AI 采集服务类。构造注入 tavily/llm，测试可换 fake。"""

    def __init__(
        self,
        tavily: Optional[TavilyClient] = None,
        llm: Optional[LLMProvider] = None,
        browser: Optional[BrowserFetcher] = None,
    ):
        self._tavily = tavily or TavilyClient()
        self._llm_injected = llm is not None
        self._llm = llm or get_llm_provider()
        # 登录墙站点（如小红书）浏览器兜底抓取；测试可注入 FakeBrowser
        self._browser = browser or BrowserFetcher()

    # ------------------------------------------------------------------ #
    # 提交任务
    # ------------------------------------------------------------------ #
    def create_ai_job(self, db: Session, data: AICollectionCreate, actor: str = "system") -> AICollectionJobResponse:
        """创建 AI 采集任务并入队后台执行。

        手动模式（manual）：跳过 Tavily 搜索，用用户粘贴的 URL+正文直接 LLM 抽取，
        用于小红书等登录墙/反爬站点（Tavily 抓不到正文）。
        """
        is_manual = data.mode == "manual"

        if not is_manual and not settings.TAVILY_API_KEY:
            raise ValueError("TAVILY_NOT_CONFIGURED")

        if is_manual:
            content = data.manual_content or ""
            if not content.strip():
                raise ValueError("手动模式需要提供粘贴的正文内容")
            # URL 可选：粘贴的是结构化菜谱 JSON（AI 生成）时可留空，否则需来源 URL。
            # 判定复用 _try_parse_structured_recipe，与后台抽取路径保持一致，避免前后漂移。
            if not (data.manual_url or "").strip() and self._try_parse_structured_recipe(content) is None:
                raise ValueError("手动模式需要提供来源 URL，或粘贴结构化菜谱 JSON")
        elif not (data.request_text or "").strip():
            raise ValueError("请输入菜名/食材")

        if data.mode == "complete":
            if not data.target_recipe_id:
                raise ValueError("补全模式需要指定 target_recipe_id")
            target = db.query(Recipe).filter(Recipe.id == data.target_recipe_id).first()
            if not target:
                raise ValueError("目标菜谱不存在")

        # 站点限制：任务指定优先，缺省回落全局配置 AI_COLLECT_SEARCH_SITES（手动模式不适用）
        raw_sites = getattr(data, "search_sites", None)
        search_sites = self._default_search_sites() if raw_sites is None else self._normalize_sites(raw_sites)

        job = IngestionJob(
            id=str(uuid.uuid4()),
            status="queued",
            stage="submitted",
            job_type="ai_search",
            request_text=data.request_text or "",
            collection_mode=data.mode,
            target_recipe_id=data.target_recipe_id if data.mode == "complete" else None,
            max_results=min(data.max_results, settings.AI_COLLECT_MAX_PAGES),
            candidates_count=0,
            llm_provider=getattr(data, "llm_provider", None),
            llm_model=getattr(data, "llm_model", None),
            search_domains_json=json.dumps(search_sites) if search_sites else None,
            manual_url=(data.manual_url or "").strip() if is_manual else None,
            manual_content=data.manual_content if is_manual else None,
        )
        repo = AICollectionRepository(db)
        job = repo.create_job(job)
        executor.enqueue_ai_collect(job.id)
        return self._job_response(db, job)

    # ------------------------------------------------------------------ #
    # 后台采集流水线
    # ------------------------------------------------------------------ #
    def _collect(self, job_id: str) -> None:
        """后台线程入口；独立 DB session，异常不外抛。"""
        try:
            with get_db_context() as db:
                self._run_collection(db, job_id)
        except TavilyUnavailableError as e:
            self._fail_job(job_id, "TAVILY_FAILED", str(e))
        except LLMUnavailableError as e:
            self._fail_job(job_id, "LLM_UNAVAILABLE", str(e))
        except Exception as e:  # noqa: BLE001 - 后台线程吞掉
            logger.exception("AI 采集任务 %s 异常", job_id)
            self._fail_job(job_id, "COLLECTION_FAILED", str(e))

    def _run_collection(self, db: Session, job_id: str) -> None:
        repo = AICollectionRepository(db)
        job = repo.get_job(job_id)
        if not job:
            logger.warning("AI采集任务 %s 不存在，跳过", job_id)
            return

        # 手动模式（小红书等登录墙站）：跳过 Tavily 搜索，直接抽取用户粘贴内容
        if job.collection_mode == "manual":
            self._run_manual_collection(db, job)
            return

        job.status = "running"
        job.stage = "fetched"
        job.started_at = job.started_at or datetime.utcnow()
        db.commit()

        query = self._build_search_query(db, job)
        if not query:
            logger.warning("任务 %s: 搜索query为空（mode=%s），标记 NO_SEARCH_RESULTS", job_id, job.collection_mode)
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return

        domains = self._job_search_domains(job)
        logger.info(
            "任务 %s: 开始采集 mode=%s query=%r llm=%s/%s 搜索范围=%s",
            job_id, job.collection_mode, query,
            job.llm_provider or settings.LLM_PROVIDER,
            job.llm_model or default_model_for(job.llm_provider),
            domains or "全网",
        )

        try:
            hits = self._tavily.search(
                query, max_results=job.max_results, include_domains=domains or None
            )
        except TavilyUnavailableError as e:
            self._finish(db, job, error_code="TAVILY_FAILED", reason=str(e))
            return
        # 防御：限定站点时，剔除 host 不在所选域名内的命中（Tavily include_domains 正常应已保证）
        if domains:
            before = len(hits)
            hits = [h for h in hits if self._host_in_domains(h.url, domains)]
            if len(hits) != before:
                logger.warning("任务 %s: %d 条命中不在限定站点内，已跳过", job_id, before - len(hits))
        logger.info("任务 %s: Tavily 命中 %d 条", job_id, len(hits))
        for h in hits:
            logger.info("任务 %s:   候选 %s | %s", job_id, h.url, h.title)

        # 精确去重：跳过已采集 URL（raw_hash = sha256(url)）
        ingestion_repo = IngestionRepository(db)
        filtered = []
        for hit in hits:
            if not hit.url:
                continue
            raw_hash = hashlib.sha256(hit.url.encode()).hexdigest()
            if ingestion_repo.get_source_by_hash(raw_hash):
                logger.info("任务 %s:   跳过已采集 %s", job_id, hit.url)
                continue
            filtered.append(hit)
        if not filtered:
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return
        logger.info("任务 %s: 去重后剩 %d 条待抓取", job_id, len(filtered))

        # 过滤搜索/分类/标签/视频等不含单道菜谱的列表型 URL：
        # 这类页面喂给 LLM 必然返回 {"title":""}（模型正确拒绝），提前过滤省调用，也让原因更明确。
        before = len(filtered)
        filtered = [h for h in filtered if not self._is_listing_url(h.url)]
        if len(filtered) != before:
            logger.warning(
                "任务 %s: 过滤掉 %d 条列表/视频型 URL（非单菜谱页），保留 %d 条",
                job_id, before - len(filtered), len(filtered),
            )
        if not filtered:
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return

        try:
            pages_ok, pages_failed = self._tavily.extract(
                [h.url for h in filtered[: settings.AI_COLLECT_MAX_PAGES]]
            )
        except TavilyUnavailableError as e:
            self._finish(db, job, error_code="TAVILY_FAILED", reason=str(e))
            return
        logger.info("任务 %s: 抓取成功 %d 页 / 失败 %d 页", job_id, len(pages_ok), len(pages_failed))
        for f in pages_failed:
            logger.warning("任务 %s:   抓取失败 %s: %s", job_id, f.get("url"), f.get("error"))

        # 清洗正文，剔除空页；登录墙站点（如小红书）Tavily 抓不到正文 → 浏览器兜底
        pages = []
        browser_urls = []
        for page in pages_ok:
            url = page.get("url") or ""
            raw = clean_page_text(page.get("raw_content", ""))
            if url and raw:
                pages.append((url, raw))
            elif url:
                logger.warning("任务 %s:   页面 %s 正文为空，跳过", job_id, url)
                if self._is_login_walled_host(url):
                    browser_urls.append(url)
        for failed in pages_failed:
            url = failed.get("url") or ""
            if url and self._is_login_walled_host(url):
                browser_urls.append(url)
        for url in browser_urls:
            raw = self._browser_fallback(db, job, url)
            if raw:
                pages.append((url, raw))

        # 任务可指定供应商/模型（用户在前端选择），否则用服务默认/配置
        llm = self._llm if self._llm_injected else self._build_job_llm(job)

        if not pages:
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return
        for url, raw in pages:
            logger.info("任务 %s:   有效页面 %s 正文 %d 字", job_id, url, len(raw))

        # 采集策略：先逐页独立抽取；仅当 ≥2 页的菜谱名（归一化后）完全相同时，
        # 才把它们综合总结为 1 份菜谱；其余各页独立成候选入库。
        # 避免把不同菜品/列表页混在一起做多来源总结导致整批被丢弃。
        extracted: List[tuple] = []
        for url, raw in pages:
            logger.info("任务 %s:   逐页抽取 %s", job_id, url)
            try:
                recipe = extract_recipe_with_fix(llm, url, raw)
            except (LLMUnavailableError, LLMValidationError) as e:
                logger.warning("任务 %s:   页面 %s 抽取失败: %s", job_id, url, e)
                job.reason = (job.reason or "") + f"[{url}] 抽取失败: {e}\n"
                continue
            recipe["source_url"] = url
            extracted.append((url, raw, recipe))

        # 按归一化标题分组；标题为空的各页用独立 key（单独校验，最终按"标题为空"拒绝）
        groups: Dict[str, List[tuple]] = {}
        for url, raw, recipe in extracted:
            key = normalize_title(recipe.get("title", "")) or uuid.uuid4().hex
            groups.setdefault(key, []).append((url, raw, recipe))

        for items in groups.values():
            urls = [u for u, _, _ in items]
            if len(items) == 1:
                url, _raw, recipe = items[0]
                self._process_extracted_recipe(db, job, recipe, [url])
                continue
            # 相同菜名 → 综合总结为 1 份（来源全部记录）；异常或校验未通过则回退逐页独立入库
            logger.info("任务 %s: %d 个同标题来源 %s 综合总结为 1 份", job_id, len(items), urls)
            try:
                recipe = extract_recipe_from_sources(llm, [(u, r) for u, r, _ in items])
                recipe["source_url"] = urls[0]
                if self._process_extracted_recipe(db, job, recipe, urls):
                    continue
            except (LLMUnavailableError, LLMValidationError) as e:
                logger.warning("任务 %s: 同标题综合总结失败 %s: %s", job_id, urls, e)
                job.reason = (job.reason or "") + f"[{','.join(urls)}] 综合总结失败，回退逐页: {e}\n"
            for url, _raw, recipe in items:
                self._process_extracted_recipe(db, job, recipe, [url])

        if job.candidates_count == 0:
            logger.warning("任务 %s: 全部来源未产出候选，标记 EXTRACTION_FAILED", job_id)
            self._finish(db, job, error_code="EXTRACTION_FAILED")
        else:
            job.status = "running"
            job.stage = "review"
            logger.info("任务 %s: 共产出 %d 个候选，进入人工审核", job_id, job.candidates_count)
            db.commit()

    def _run_manual_collection(self, db: Session, job: IngestionJob) -> None:
        """手动模式：跳过 Tavily，直接用用户粘贴的内容结构化抽取。

        两种内容形态：
        - 结构化菜谱 JSON（AI 生成）：识别后直接校验落库，跳过 LLM 抽取；
        - 网页正文（登录墙/反爬站点如小红书）：用户复制正文粘贴进来，
          走 LLM 抽取，其余走同一套抽取→候选→审核流水线。
        """
        job.status = "running"
        job.stage = "fetched"
        job.started_at = job.started_at or datetime.utcnow()
        db.commit()

        url = (job.manual_url or "").strip()
        content = (job.manual_content or "").strip()
        if not content:
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return

        # 结构化菜谱 JSON 直入：不调 LLM（LLM 宕机时仍可入库，校验走 _process_extracted_recipe 内部）
        parsed = self._try_parse_structured_recipe(content)
        if parsed is not None:
            recipe = parsed
            urls = [url] if url else self._recipe_source_urls(recipe)
            recipe["source_url"] = urls[0] if urls else ""
            logger.info(
                "任务 %s: 检测到结构化菜谱 JSON，跳过 LLM 抽取 title=%r urls=%s",
                job.id, recipe.get("title"), urls,
            )
            if self._process_extracted_recipe(db, job, recipe, urls):
                job.status = "running"
                job.stage = "review"
                logger.info("任务 %s: 结构化菜谱 JSON 产出候选，进入人工审核", job.id)
                db.commit()
            else:
                logger.warning("任务 %s: 结构化菜谱 JSON 未通过校验", job.id)
                self._finish(db, job, error_code="EXTRACTION_FAILED")
            return

        # 非结构化正文：需来源 URL，走 LLM 抽取（LLM 惰性构建，JSON 路径不触碰）
        if not url:
            logger.warning("任务 %s: 正文不是结构化 JSON 且缺少来源 URL", job.id)
            self._finish(db, job, error_code="EXTRACTION_FAILED")
            return

        llm = self._llm if self._llm_injected else self._build_job_llm(job)
        logger.info(
            "任务 %s: 手动来源 %s 正文 %d 字 llm=%s/%s",
            job.id, url, len(content),
            job.llm_provider or settings.LLM_PROVIDER,
            job.llm_model or default_model_for(job.llm_provider),
        )
        try:
            recipe = extract_recipe_with_fix(llm, url, content)
        except (LLMUnavailableError, LLMValidationError) as e:
            logger.warning("任务 %s: 手动内容抽取失败: %s", job.id, e)
            job.reason = (job.reason or "") + f"[{url}] 抽取失败: {e}\n"
            self._finish(db, job, error_code="EXTRACTION_FAILED")
            return

        recipe["source_url"] = url
        if self._process_extracted_recipe(db, job, recipe, [url]):
            job.status = "running"
            job.stage = "review"
            logger.info("任务 %s: 手动来源产出候选，进入人工审核", job.id)
            db.commit()
        else:
            logger.warning("任务 %s: 手动来源抽取结果未通过校验", job.id)
            self._finish(db, job, error_code="EXTRACTION_FAILED")

    def _browser_fallback(self, db: Session, job: IngestionJob, url: str) -> Optional[str]:
        """用本地浏览器（复用登录态）兜底抓取登录墙页面正文；失败/不可用返回 None。"""
        if not settings.BROWSER_FETCH_ENABLED:
            return None
        ok, reason = self._browser.available()
        if not ok:
            logger.info("任务 %s: 浏览器兜底不可用（%s），跳过 %s", job.id, reason, url)
            return None
        try:
            raw = self._browser.fetch(url)
        except BrowserFetchError as e:
            msg = f"[{url}] 浏览器兜底抓取失败: {e}\n"
            logger.warning("任务 %s: %s", job.id, msg.strip())
            job.reason = (job.reason or "") + msg
            return None
        logger.info("任务 %s: 浏览器兜底抓到 %s 正文 %d 字", job.id, url, len(raw))
        return raw

    def _build_search_query(self, db: Session, job: IngestionJob) -> str:
        """按模式构造搜索查询。"""
        text = (job.request_text or "").strip()
        if job.collection_mode == "ingredients":
            # 兼容逗号/顿号分隔的食材
            normalized = re.sub(r"[，,]+", "、", text)
            return f"{normalized} 菜谱 做法"
        if job.collection_mode == "complete":
            target = None
            if job.target_recipe_id:
                target = db.query(Recipe).filter(Recipe.id == job.target_recipe_id).first()
            if target and target.title:
                return f"{target.title} 完整做法 食材 步骤"
            return ""
        return f"{text} 菜谱 做法"

    @staticmethod
    def _build_job_llm(job: IngestionJob) -> LLMProvider:
        """按任务记录的供应商/模型构造 LLM Provider（缺省回落配置）。"""
        provider = job.llm_provider or settings.LLM_PROVIDER
        model = job.llm_model or default_model_for(provider)
        return build_llm_provider(provider, model)

    @staticmethod
    def _is_listing_url(url: str) -> bool:
        """粗略识别搜索/分类/标签/视频等不含单道菜谱的列表型 URL。

        这类页面没有单道完整菜谱（食材+步骤），喂给 LLM 必然返回 {"title":""}。
        用 unquote 解码后再匹配，兼容 %E6%90%9C%E5%B0%8B（搜尋）这类编码路径。
        """
        lowered = unquote(url or "").lower()
        if any(host in lowered for host in (
            "youtube.com", "youtu.be", "bilibili.com", "tiktok.com", "douyin.com",
        )):
            return True
        for hint in (
            "/search/", "/搜尋/", "/category/", "/categories/",
            "/tag/", "/tags/", "/recipe-ideas/",
        ):
            if hint in lowered:
                return True
        for qp in ("?q=", "?search=", "?keyword=", "?query="):
            if qp in lowered:
                return True
        return False

    @staticmethod
    def _is_login_walled_host(url: str) -> bool:
        """登录墙/反爬站点 host 判断（Tavily extract 拿不到正文，需浏览器兜底）。"""
        try:
            host = urlparse(url).netloc.lower()
        except ValueError:
            return False
        return any(host == d or host.endswith("." + d) for d in ("xiaohongshu.com", "xhslink.com"))

    @staticmethod
    def _normalize_sites(sites) -> List[str]:
        """规范化域名列表：去空白/小写/去空去重。"""
        out = []
        for s in sites or []:
            s = (s or "").strip().lower()
            if s and s not in out:
                out.append(s)
        return out

    @staticmethod
    def _default_search_sites() -> List[str]:
        """全局默认搜索站点（AI_COLLECT_SEARCH_SITES 逗号分隔）→ 规范化域名列表。"""
        raw = settings.AI_COLLECT_SEARCH_SITES or ""
        return AiCollectionService._normalize_sites(raw.split(","))

    @staticmethod
    def _job_search_domains(job: IngestionJob) -> List[str]:
        """解析任务存储的搜索域名列表（search_domains_json）。"""
        if not job.search_domains_json:
            return []
        try:
            data = json.loads(job.search_domains_json)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, list):
            return []
        return AiCollectionService._normalize_sites(data)

    @staticmethod
    def _host_in_domains(url: str, domains: List[str]) -> bool:
        """URL host 是否属于限定域名（等于域名或以 '.' + 域名 结尾）。"""
        try:
            host = urlparse(url).netloc.lower()
        except ValueError:
            return False
        return any(host == d or host.endswith("." + d) for d in domains)

    # ------------------------------------------------------------------ #
    # 结构化菜谱 JSON 直入
    # ------------------------------------------------------------------ #
    @staticmethod
    def _try_parse_structured_recipe(content) -> Optional[dict]:
        """把粘贴内容当结构化菜谱 JSON 解析；不是 JSON dict 或 title 为空返回 None。

        判定规则（前端 lookStructuredRecipe 同构镜像，注意两者对非标准 JSON 的差异：
        后端 json.loads 容忍 NaN/Infinity，前端 JSON.parse 拒绝 → 前端更严只会让用户
        多填来源 URL，漂移只发生在安全方向）：
        1. 去首尾空白与 BOM（\\ufeff）；
        2. 兼容 Markdown 代码围栏 ```json ... ```（大小写不敏感）；
        3. 严格 JSON 解析；
        4. 顶层必须是 dict 且 title（strip 后）非空。
        仅凭 title 判定"意图直入"；食材/步骤缺失交给 validate_recipe_reason 显式报错，
        避免把 {"title":"x"} 这类输入静默丢回 LLM。
        """
        text = (content or "").strip()
        if not text:
            return None
        if len(text) > _MAX_STRUCTURED_JSON_CHARS:
            return None
        text = text.lstrip("\ufeff")
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        if not str(data.get("title") or "").strip():
            return None
        return data

    @staticmethod
    def _recipe_source_urls(recipe: dict) -> List[str]:
        """取 JSON 自带 source_url 作为候选来源；仅接受 http(s)（防 javascript: 等注入）。"""
        url = (recipe.get("source_url") or "").strip()
        if url.startswith(("http://", "https://")):
            return [url]
        return []

    # ------------------------------------------------------------------ #
    # 落库
    # ------------------------------------------------------------------ #
    def _process_extracted_recipe(
        self, db: Session, job: IngestionJob, recipe: dict, urls: List[str],
    ) -> bool:
        """校验 → 去重 → 落库候选。返回是否已处理：
        True=已落库或已存在（去重命中）；False=校验未通过（调用方应回退逐页抽取）。"""
        vreason = validate_recipe_reason(recipe)
        if vreason:
            msg = f"[{','.join(urls)}] 校验未通过（{vreason}）"
            logger.info("任务 %s: %s title=%r", job.id, msg, recipe.get("title"))
            job.reason = (job.reason or "") + msg + "\n"
            return False
        dedup_key = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
        if AICollectionRepository(db).get_by_dedup_key(dedup_key):
            logger.info("任务 %s: 标题去重命中 %r，跳过", job.id, recipe["title"])
            return True
        match_scores = self._find_duplicates(db, recipe)
        self._persist_candidate(db, job, recipe, urls, dedup_key, match_scores)
        job.candidates_count += 1
        logger.info(
            "任务 %s: 候选入库 title=%r 食材%d 调料%d 步骤%d urls=%s",
            job.id, recipe["title"], len(recipe.get("ingredients", [])),
            len(recipe.get("seasonings", [])), len(recipe.get("steps", [])), urls,
        )
        db.commit()
        return True

    def _persist_candidate(
        self, db: Session, job: IngestionJob, recipe: dict,
        urls: List[str], dedup_key: str, match_scores: dict,
    ) -> None:
        """把抽取结果落库为 review 候选 + IngestionCandidate。

        urls 为该候选参考的全部来源 URL：逐个建 RecipeSource（raw_hash 去重生效），
        主来源（第一个）写入 recipe/candidate.source_id，全部 URL 记录到 source_urls_json。
        食材/调料已由 validate_recipe_reason 拆好；此处再用调料表兜底一次（静态词典
        未覆盖、但调料表中已维护的名字），然后把调料落为 RecipeSeasoning 关联。
        """
        source_rows = []
        for url in urls:
            url = (url or "").strip()
            if not url:
                continue
            source_rows.append(RecipeSource(
                id=str(uuid.uuid4()),
                source_type="url",
                source_url=url,
                raw_hash=hashlib.sha256(url.encode()).hexdigest(),
                fetched_at=datetime.utcnow(),
            ))
        if source_rows:
            db.add_all(source_rows)
            db.flush()
        primary_source = source_rows[0] if source_rows else None

        cand_recipe = Recipe(
            id=str(uuid.uuid4()),
            title=recipe["title"],
            pinyin=to_pinyin(recipe["title"]),
            summary=recipe.get("summary"),
            servings=recipe.get("servings"),
            prep_minutes=recipe.get("prep_minutes"),
            cook_minutes=recipe.get("cook_minutes"),
            difficulty=recipe.get("difficulty"),
            status="review",
            source_id=primary_source.id if primary_source else None,
            revision=1,
            created_by="ai_search",
        )
        db.add(cand_recipe)
        db.flush()

        # 采集菜谱自动分类：显式 category（结构化 JSON 提供）优先，新分类名自动创建；否则按标题规则（回落默认）
        db.add(RecipeCategoryLink(
            id=str(uuid.uuid4()),
            recipe_id=cand_recipe.id,
            category_id=resolve_category_id(
                db, "recipe",
                name=resolve_recipe_category(recipe["title"], recipe.get("category")),
            ),
        ))

        # 调料兜底：静态词典未覆盖、但调料表中已维护的名字（用户手工新增的调料）→ 拆到调料
        seasoning_repo = SeasoningRepository(db)
        known_seasonings = {s.canonical_name for s in seasoning_repo.list_all()}
        ingredients = recipe.get("ingredients", [])
        seasonings = list(recipe.get("seasonings", []) or [])
        seen_seasonings = {s["name"] for s in seasonings if s.get("name")}
        residual = []
        for ing in ingredients:
            name = (ing.get("name") or "").strip()
            if name and name in known_seasonings and name not in seen_seasonings:
                seasonings.append(ing)
                seen_seasonings.add(name)
            else:
                residual.append(ing)
        recipe["ingredients"] = residual
        recipe["seasonings"] = seasonings

        ingredient_repo = IngredientRepository(db)
        for i, ing in enumerate(recipe["ingredients"]):
            name = (ing.get("name") or "").strip()
            if not name:
                continue
            ingredient = ingredient_repo.get_by_name(name)
            if not ingredient:
                # 食材按名称自动分类（入库规则；未识别回落默认）
                cat_name = classify_ingredient(name)
                ingredient = Ingredient(
                    id=str(uuid.uuid4()),
                    canonical_name=name,
                    confidence_status="candidate",
                    category_id=resolve_category_id(db, "ingredient", name=cat_name),
                )
                db.add(ingredient)
                db.flush()
            db.add(RecipeIngredient(
                id=str(uuid.uuid4()),
                recipe_id=cand_recipe.id,
                ingredient_id=ingredient.id,
                quantity=ing.get("quantity"),
                unit=ing.get("unit"),
                raw_quantity=ing.get("raw_quantity"),
                preparation=ing.get("preparation"),
                optional=1 if ing.get("optional") else 0,
                sort_order=i,
            ))

        # 调料：查找或创建 Seasoning，落 RecipeSeasoning 关联（按名去重，表上有唯一约束）
        for ing in recipe["seasonings"]:
            name = (ing.get("name") or "").strip()
            if not name:
                continue
            seasoning = seasoning_repo.get_by_name(name)
            if not seasoning:
                # 调料按名称自动分类（入库规则；未识别回落默认）
                seasoning = Seasoning(
                    id=str(uuid.uuid4()),
                    canonical_name=name,
                    pinyin=to_pinyin(name),
                    category_id=resolve_category_id(db, "seasoning", name=classify_seasoning(name)),
                )
                db.add(seasoning)
                db.flush()
            db.add(RecipeSeasoning(
                id=str(uuid.uuid4()),
                recipe_id=cand_recipe.id,
                seasoning_id=seasoning.id,
                quantity=self._seasoning_quantity(ing),
            ))

        for step in recipe.get("steps", []):
            db.add(RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=cand_recipe.id,
                step_no=step["step_no"],
                instruction=step["instruction"],
                duration_minutes=step.get("duration_minutes"),
            ))

        tags = recipe.get("tags") or []
        if tags:
            self._add_tags(db, cand_recipe.id, tags)

        candidate = IngestionCandidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            recipe_id=cand_recipe.id,
            source_id=primary_source.id if primary_source else None,
            source_urls_json=json.dumps(
                [s.source_url for s in source_rows], ensure_ascii=False
            ),
            target_recipe_id=job.target_recipe_id if job.collection_mode == "complete" else None,
            action="pending",
            merge_mode="merge" if job.collection_mode == "complete" else "new",
            dedup_key=dedup_key,
            normalized_title=normalize_title(recipe["title"]),
            core_ingredients_json=json.dumps(
                [i.get("name") for i in recipe.get("ingredients", [])], ensure_ascii=False
            ),
            match_scores_json=json.dumps(match_scores, ensure_ascii=False),
        )
        db.add(candidate)
        db.flush()

    @staticmethod
    def _seasoning_quantity(ing: dict) -> Optional[str]:
        """把调料条目的用量整理成字符串（优先原始文本，其次 数值+单位）。"""
        raw = (ing.get("raw_quantity") or ing.get("amount") or "").strip()
        if raw:
            return raw
        q = ing.get("quantity")
        u = ing.get("unit")
        if q is not None and u:
            return f"{q}{u}"
        return str(q) if q is not None else None

    @staticmethod
    def _add_tags(db: Session, recipe_id: str, tags: List[str]) -> None:
        """查找或创建标签并建立关联（不 commit）。"""
        for tag_name in tags:
            name = (tag_name or "").strip()
            if not name:
                continue
            tag = db.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = Tag(name=name, type="cuisine")
                db.add(tag)
                db.flush()
            exists = db.query(RecipeTag).filter(
                RecipeTag.recipe_id == recipe_id, RecipeTag.tag_id == tag.id
            ).first()
            if not exists:
                db.add(RecipeTag(recipe_id=recipe_id, tag_id=tag.id))

    def _find_duplicates(self, db: Session, recipe: dict) -> dict:
        """与已存在非软删菜谱的重叠判定（标题 + 核心食材），供审核参考。"""
        title_norm = normalize_title(recipe["title"])
        cand_names = {i.get("name") for i in recipe.get("ingredients", []) if i.get("name")}
        scores: dict = {}

        rows = db.execute(
            select(
                Recipe.id, Recipe.title, Recipe.status, Ingredient.canonical_name,
            )
            .outerjoin(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
            .outerjoin(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
            .where(Recipe.deleted_at.is_(None))
        ).all()

        by_recipe: dict = {}
        for rid, title, status, name in rows:
            entry = by_recipe.setdefault(rid, {"title": title, "status": status, "ingredients": set()})
            if name:
                entry["ingredients"].add(name)

        for rid, entry in by_recipe.items():
            if normalize_title(entry["title"]) == title_norm:
                scores.setdefault("title_duplicates", []).append(
                    {"recipe_id": rid, "title": entry["title"], "status": entry["status"], "score": 1.0}
                )
            entry_names = entry["ingredients"]
            if entry_names and cand_names:
                overlap = len(cand_names & entry_names) / min(len(cand_names), len(entry_names))
                if overlap >= 0.6:
                    scores.setdefault("ingredient_overlaps", []).append(
                        {"recipe_id": rid, "title": entry["title"],
                         "status": entry["status"], "overlap": round(overlap, 2)}
                    )
        return scores

    # ------------------------------------------------------------------ #
    # 人工审核
    # ------------------------------------------------------------------ #
    def review_candidate(
        self, db: Session, candidate_id: str, action: str, actor: str = "system"
    ) -> Optional[CandidateResponse]:
        """审核候选：approve（new=发布/merge=合入目标）或 reject（软删候选）。"""
        repo = AICollectionRepository(db)
        candidate = repo.get_candidate(candidate_id)
        if not candidate:
            return None
        if candidate.action != "pending":
            raise ValueError("该候选已处理")

        if action == "approve":
            if candidate.merge_mode == "merge":
                self._merge_into_target(db, candidate)
                candidate.action = "merged"
            else:
                recipe_repo = RecipeRepository(db)
                recipe = recipe_repo.publish_recipe(candidate.recipe_id)
                if not recipe:
                    raise ValueError("候选菜谱不存在")
                candidate.action = "approved"
                executor.enqueue_index(candidate.recipe_id)
        elif action == "reject":
            if candidate.recipe:
                candidate.recipe.deleted_at = datetime.utcnow()
            candidate.action = "rejected"
        else:
            raise ValueError("未知审核动作")

        candidate.reviewed_by = actor
        candidate.reviewed_at = datetime.utcnow()
        db.commit()

        self._finalize_job(db, candidate.job_id)
        return self._candidate_response(db, candidate)

    def _merge_into_target(self, db: Session, candidate: IngestionCandidate) -> None:
        """补全模式合并：只补缺失字段、保留目标标题与来源、合并前留快照、revision+1。"""
        target = candidate.target_recipe
        cand_recipe = candidate.recipe
        if not target:
            raise ValueError("补全目标不存在")
        if not cand_recipe:
            raise ValueError("候选菜谱不存在")

        # 合并前快照（复用 RecipeRevision 表）
        db.add(RecipeRevision(
            id=str(uuid.uuid4()),
            recipe_id=target.id,
            revision_no=target.revision,
            title=target.title,
            summary=target.summary,
            servings=target.servings,
            prep_minutes=target.prep_minutes,
            cook_minutes=target.cook_minutes,
            difficulty=target.difficulty,
            status=target.status,
            source_id=target.source_id,
            version_note=f"AI采集合并前快照 (job={candidate.job_id})",
        ))

        # 顶层字段：只补缺失
        for field in ("summary", "cover", "servings", "prep_minutes", "cook_minutes", "difficulty"):
            if getattr(target, field) in (None, "") and getattr(cand_recipe, field) not in (None, ""):
                setattr(target, field, getattr(cand_recipe, field))

        # 食材：按 canonical_name 去重追加
        existing_names = {ri.ingredient.canonical_name for ri in target.recipe_ingredients if ri.ingredient}
        next_order = max([ri.sort_order for ri in target.recipe_ingredients] or [-1]) + 1
        for ri in cand_recipe.recipe_ingredients:
            name = ri.ingredient.canonical_name if ri.ingredient else ""
            if name and name not in existing_names:
                db.add(RecipeIngredient(
                    id=str(uuid.uuid4()),
                    recipe_id=target.id,
                    ingredient_id=ri.ingredient_id,
                    quantity=ri.quantity,
                    unit=ri.unit,
                    raw_quantity=ri.raw_quantity,
                    preparation=ri.preparation,
                    optional=ri.optional,
                    sort_order=next_order,
                ))
                existing_names.add(name)
                next_order += 1

        # 调料：按 canonical_name 去重追加
        existing_seasonings = {
            rs.seasoning.canonical_name for rs in target.recipe_seasonings if rs.seasoning
        }
        for rs in cand_recipe.recipe_seasonings:
            name = rs.seasoning.canonical_name if rs.seasoning else ""
            if name and name not in existing_seasonings:
                db.add(RecipeSeasoning(
                    id=str(uuid.uuid4()),
                    recipe_id=target.id,
                    seasoning_id=rs.seasoning_id,
                    quantity=rs.quantity,
                ))
                existing_seasonings.add(name)

        # 步骤：target 无则全量复制，有则追加不重复
        target_steps = sorted(target.recipe_steps, key=lambda s: s.step_no)
        cand_steps = sorted(cand_recipe.recipe_steps, key=lambda s: s.step_no)
        existing_inst = {s.instruction.strip() for s in target_steps}
        if not target_steps:
            for s in cand_steps:
                db.add(RecipeStep(
                    id=str(uuid.uuid4()),
                    recipe_id=target.id,
                    step_no=s.step_no,
                    instruction=s.instruction,
                    duration_minutes=s.duration_minutes,
                ))
        else:
            next_no = max(s.step_no for s in target_steps) + 1
            for s in cand_steps:
                if s.instruction.strip() not in existing_inst:
                    db.add(RecipeStep(
                        id=str(uuid.uuid4()),
                        recipe_id=target.id,
                        step_no=next_no,
                        instruction=s.instruction,
                        duration_minutes=s.duration_minutes,
                    ))
                    existing_inst.add(s.instruction.strip())
                    next_no += 1

        # 标签 union
        target_tag_names = {
            t.name for t in db.query(Tag)
            .join(RecipeTag, RecipeTag.tag_id == Tag.id)
            .filter(RecipeTag.recipe_id == target.id).all()
        }
        cand_tags = (
            db.query(Tag).join(RecipeTag, RecipeTag.tag_id == Tag.id)
            .filter(RecipeTag.recipe_id == cand_recipe.id).all()
        )
        for t in cand_tags:
            if t.name not in target_tag_names:
                db.add(RecipeTag(recipe_id=target.id, tag_id=t.id))
                target_tag_names.add(t.name)

        # 来源：target 为空才置候选来源，否则保留
        if not target.source_id:
            target.source_id = candidate.source_id

        target.revision += 1
        target.updated_at = datetime.utcnow()

        # 候选已被合并，软删避免出现在菜谱库
        cand_recipe.deleted_at = datetime.utcnow()
        db.commit()

        executor.enqueue_index(target.id)

    def _finalize_job(self, db: Session, job_id: str) -> None:
        """任务无待审候选时收敛状态。"""
        repo = AICollectionRepository(db)
        job = repo.get_job(job_id)
        if not job:
            return
        if repo.count_pending(job_id) > 0:
            return
        job.status = "succeeded" if repo.count_approved(job_id) > 0 else "rejected"
        job.finished_at = datetime.utcnow()
        db.commit()

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def get_job_detail(self, db: Session, job_id: str) -> Optional[AICollectionJobResponse]:
        repo = AICollectionRepository(db)
        job = repo.get_job(job_id)
        if not job:
            return None
        return self._job_response(db, job)

    def list_pending(self, db: Session, page: int, page_size: int) -> PaginatedCandidateResponse:
        repo = AICollectionRepository(db)
        items, total = repo.list_pending(page, page_size)
        return PaginatedCandidateResponse(
            data=[self._candidate_response(db, c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    def _append_cloud_models(
        models: List[LLMModelOption], provider: str, label: str,
        api_key: Optional[str], base_url: str, default_model: str,
    ) -> None:
        """追加 OpenAI 兼容云端模型选项：优先枚举真实模型，失败回落配置默认模型。"""
        if not api_key:
            return
        try:
            names = OpenAICompatLLMProvider(
                api_key=api_key, base_url=base_url, model=default_model
            ).list_models()
        except LLMUnavailableError:
            names = [default_model]
        for name in names:
            models.append(LLMModelOption(provider=provider, model=name, label=f"{label} {name}"))

    def list_models(self) -> LLMModelsResponse:
        """可用模型列表：Ollama 在线模型 + Anthropic/DeepSeek/OpenRouter/通用端点可选。"""
        models: List[LLMModelOption] = []
        try:
            for name in OllamaLLMProvider().list_models():
                models.append(LLMModelOption(provider="ollama", model=name, label=f"本地 {name}"))
        except LLMUnavailableError:
            pass  # Ollama 不可达，仅返回云端选项

        if settings.LLM_API_KEY:
            models.append(LLMModelOption(
                provider="anthropic",
                model=settings.ANTHROPIC_LLM_MODEL,
                label=f"云端 {settings.ANTHROPIC_LLM_MODEL}",
            ))

        # OpenAI 兼容云端供应商（DeepSeek / OpenRouter / 通用端点）
        self._append_cloud_models(
            models, "deepseek", "DeepSeek",
            settings.DEEPSEEK_API_KEY or settings.LLM_API_KEY,
            settings.DEEPSEEK_BASE_URL, settings.DEEPSEEK_MODEL,
        )
        self._append_cloud_models(
            models, "openrouter", "OpenRouter",
            settings.OPENROUTER_API_KEY or settings.LLM_API_KEY,
            settings.OPENROUTER_BASE_URL, settings.OPENROUTER_MODEL,
        )
        self._append_cloud_models(
            models, "openai_compat", "OpenAI兼容",
            settings.OPENAI_COMPAT_API_KEY or settings.LLM_API_KEY,
            settings.OPENAI_COMPAT_BASE_URL or settings.LLM_BASE_URL, settings.OPENAI_COMPAT_MODEL,
        )

        return LLMModelsResponse(
            models=models,
            default_provider=settings.LLM_PROVIDER,
            default_model=default_model_for(settings.LLM_PROVIDER),
        )

    def config_status(self) -> ConfigStatusResponse:
        llm_provider = settings.LLM_PROVIDER
        llm_configured = {
            "ollama": True,
            "anthropic": bool(settings.LLM_API_KEY),
            "deepseek": bool(settings.DEEPSEEK_API_KEY or settings.LLM_API_KEY),
            "openrouter": bool(settings.OPENROUTER_API_KEY or settings.LLM_API_KEY),
            "openai_compat": bool(settings.OPENAI_COMPAT_API_KEY or settings.LLM_API_KEY),
        }.get(llm_provider, True)  # 未知供应商按已配置处理，运行期报错
        llm_model = default_model_for(llm_provider)
        try:
            llm_health = self._llm.health_check()
        except Exception as e:  # noqa: BLE001 - 健康检查吞掉
            llm_health = {"ok": False, "model_available": False, "detail": str(e)}
        return ConfigStatusResponse(
            tavily_configured=bool(settings.TAVILY_API_KEY),
            llm_provider=llm_provider,
            llm_configured=llm_configured,
            llm_model=llm_model,
            llm_health=llm_health,
            default_search_sites=self._default_search_sites(),
        )

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    @staticmethod
    def _finish(db: Session, job: IngestionJob, error_code: Optional[str] = None,
                reason: Optional[str] = None) -> None:
        if error_code:
            job.status = "failed"
            job.error_code = error_code
            job.finished_at = datetime.utcnow()
        if reason:
            job.reason = (job.reason or "") + reason
        db.commit()

    def _fail_job(self, job_id: str, error_code: str, reason: Optional[str] = None) -> None:
        try:
            with get_db_context() as db:
                job = AICollectionRepository(db).get_job(job_id)
                if job and job.status not in ("succeeded", "failed", "rejected"):
                    job.status = "failed"
                    job.error_code = error_code
                    if reason:
                        job.reason = (job.reason or "") + reason
                    job.finished_at = datetime.utcnow()
        except Exception:  # noqa: BLE001
            logger.exception("更新采集任务失败状态异常")

    def _recipe_response(self, db: Session, recipe: Recipe):
        from app.services.recipe_service import RecipeService
        service = RecipeService(RecipeRepository(db), IngredientRepository(db))
        return service._to_response(recipe)

    def _candidate_response(self, db: Session, candidate: IngestionCandidate) -> CandidateResponse:
        match_scores: dict = {}
        core_ingredients: List[str] = []
        if candidate.match_scores_json:
            try:
                match_scores = json.loads(candidate.match_scores_json)
            except (ValueError, TypeError):
                match_scores = {}
        if candidate.core_ingredients_json:
            try:
                core_ingredients = json.loads(candidate.core_ingredients_json)
            except (ValueError, TypeError):
                core_ingredients = []
        source_urls: List[str] = []
        if candidate.source_urls_json:
            try:
                source_urls = json.loads(candidate.source_urls_json)
            except (ValueError, TypeError):
                source_urls = []
        source_url = candidate.source.source_url if candidate.source else None
        recipe = self._recipe_response(db, candidate.recipe) if candidate.recipe else None
        return CandidateResponse(
            id=candidate.id,
            job_id=candidate.job_id,
            recipe=recipe,
            action=candidate.action,
            merge_mode=candidate.merge_mode,
            source_url=source_url,
            source_urls=source_urls,
            normalized_title=candidate.normalized_title,
            core_ingredients=core_ingredients,
            match_scores=match_scores,
            reason=candidate.reason,
            reviewed_by=candidate.reviewed_by,
            reviewed_at=candidate.reviewed_at,
            created_at=candidate.created_at,
        )

    def _job_response(self, db: Session, job: IngestionJob) -> AICollectionJobResponse:
        repo = AICollectionRepository(db)
        candidates = repo.list_by_job(job.id)
        return AICollectionJobResponse(
            id=job.id,
            source_id=job.source_id,
            status=job.status,
            stage=job.stage,
            error_code=job.error_code,
            result_recipe_id=job.result_recipe_id,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
            request_text=job.request_text,
            collection_mode=job.collection_mode,
            target_recipe_id=job.target_recipe_id,
            candidates_count=job.candidates_count,
            reason=job.reason,
            llm_provider=job.llm_provider,
            llm_model=job.llm_model,
            search_sites=self._job_search_domains(job) or None,
            manual_url=job.manual_url,
            candidates=[self._candidate_response(db, c) for c in candidates],
        )
