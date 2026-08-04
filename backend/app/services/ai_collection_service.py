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
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.pinyin import to_pinyin
from app.db.database import get_db_context
from app.db.models import (
    IngestionCandidate, IngestionJob, Ingredient, Recipe,
    RecipeIngredient, RecipeRevision, RecipeSource, RecipeStep,
    RecipeTag, Tag,
)
from app.llm import (
    LLMProvider, LLMUnavailableError, LLMValidationError,
    build_llm_provider, get_llm_provider,
)
from app.llm.ollama import OllamaLLMProvider
from app.llm.prompts import (
    extract_recipe_from_sources, extract_recipe_with_fix,
    normalize_title, validate_recipe,
)
from app.repositories.ai_collection_repository import AICollectionRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.repositories.recipe_repository import RecipeRepository
from app.schemas.ai_collection import (
    AICollectionCreate, AICollectionJobResponse, CandidateResponse,
    ConfigStatusResponse, LLMModelOption, LLMModelsResponse,
    PaginatedCandidateResponse,
)
from app.services.tavily_client import TavilyClient, TavilyUnavailableError, clean_page_text
from app.tasks import executor

logger = logging.getLogger(__name__)


class AiCollectionService:
    """AI 采集服务类。构造注入 tavily/llm，测试可换 fake。"""

    def __init__(self, tavily: Optional[TavilyClient] = None, llm: Optional[LLMProvider] = None):
        self._tavily = tavily or TavilyClient()
        self._llm_injected = llm is not None
        self._llm = llm or get_llm_provider()

    # ------------------------------------------------------------------ #
    # 提交任务
    # ------------------------------------------------------------------ #
    def create_ai_job(self, db: Session, data: AICollectionCreate, actor: str = "system") -> AICollectionJobResponse:
        """创建 AI 采集任务并入队后台执行。"""
        if not settings.TAVILY_API_KEY:
            raise ValueError("TAVILY_NOT_CONFIGURED")

        if data.mode == "complete":
            if not data.target_recipe_id:
                raise ValueError("补全模式需要指定 target_recipe_id")
            target = db.query(Recipe).filter(Recipe.id == data.target_recipe_id).first()
            if not target:
                raise ValueError("目标菜谱不存在")

        job = IngestionJob(
            id=str(uuid.uuid4()),
            status="queued",
            stage="submitted",
            job_type="ai_search",
            request_text=data.request_text,
            collection_mode=data.mode,
            target_recipe_id=data.target_recipe_id if data.mode == "complete" else None,
            max_results=min(data.max_results, settings.AI_COLLECT_MAX_PAGES),
            candidates_count=0,
            llm_provider=getattr(data, "llm_provider", None),
            llm_model=getattr(data, "llm_model", None),
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
            return

        job.status = "running"
        job.stage = "fetched"
        job.started_at = job.started_at or datetime.utcnow()
        db.commit()

        query = self._build_search_query(db, job)
        if not query:
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return

        try:
            hits = self._tavily.search(query, max_results=job.max_results)
        except TavilyUnavailableError as e:
            self._finish(db, job, error_code="TAVILY_FAILED", reason=str(e))
            return

        # 精确去重：跳过已采集 URL（raw_hash = sha256(url)）
        ingestion_repo = IngestionRepository(db)
        filtered = []
        for hit in hits:
            if not hit.url:
                continue
            raw_hash = hashlib.sha256(hit.url.encode()).hexdigest()
            if ingestion_repo.get_source_by_hash(raw_hash):
                continue
            filtered.append(hit)
        if not filtered:
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return

        try:
            pages_ok, _failed = self._tavily.extract(
                [h.url for h in filtered[: settings.AI_COLLECT_MAX_PAGES]]
            )
        except TavilyUnavailableError as e:
            self._finish(db, job, error_code="TAVILY_FAILED", reason=str(e))
            return

        # 清洗正文，剔除空页
        pages = []
        for page in pages_ok:
            url = page.get("url") or ""
            raw = clean_page_text(page.get("raw_content", ""))
            if url and raw:
                pages.append((url, raw))

        # 任务可指定供应商/模型（用户在前端选择），否则用服务默认/配置
        llm = self._llm if self._llm_injected else self._build_job_llm(job)

        if not pages:
            self._finish(db, job, error_code="NO_SEARCH_RESULTS")
            return

        # 多来源交叉总结：每批 ≤ AI_COLLECT_MAX_SOURCES 个来源综合成一份菜谱；
        # 批总结失败时回退到批内逐页抽取，避免整批丢失。
        for batch in self._group_pages(pages):
            batch_urls = [u for u, _ in batch]
            if len(batch) >= settings.AI_COLLECT_MIN_SOURCES:
                try:
                    recipe = extract_recipe_from_sources(llm, batch)
                    recipe["source_url"] = batch_urls[0]
                    self._process_extracted_recipe(db, job, recipe, batch_urls)
                    continue
                except (LLMUnavailableError, LLMValidationError) as e:
                    logger.warning("多来源总结 %s 失败，回退逐页抽取: %s", batch_urls, e)
                    job.reason = (
                        (job.reason or "")
                        + f"[{','.join(batch_urls)}] 多来源总结失败，回退逐页: {e}\n"
                    )
            for url, raw in batch:
                try:
                    recipe = extract_recipe_with_fix(llm, url, raw)
                except (LLMUnavailableError, LLMValidationError) as e:
                    logger.warning("页面 %s 抽取失败: %s", url, e)
                    job.reason = (job.reason or "") + f"[{url}] 抽取失败: {e}\n"
                    continue
                recipe["source_url"] = url
                self._process_extracted_recipe(db, job, recipe, [url])

        if job.candidates_count == 0:
            self._finish(db, job, error_code="EXTRACTION_FAILED")
        else:
            job.status = "running"
            job.stage = "review"
            db.commit()

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
        if provider == "anthropic":
            model = job.llm_model or settings.ANTHROPIC_LLM_MODEL
        else:
            model = job.llm_model or settings.LLM_MODEL
        return build_llm_provider(provider, model)

    @staticmethod
    def _group_pages(pages: List[tuple]) -> List[List[tuple]]:
        """把 [(url, raw), ...] 按每批最多 AI_COLLECT_MAX_SOURCES 个来源切批。"""
        size = max(1, settings.AI_COLLECT_MAX_SOURCES)
        return [pages[i:i + size] for i in range(0, len(pages), size)]

    # ------------------------------------------------------------------ #
    # 落库
    # ------------------------------------------------------------------ #
    def _process_extracted_recipe(
        self, db: Session, job: IngestionJob, recipe: dict, urls: List[str],
    ) -> None:
        """校验 → 去重 → 落库候选。recipe 需已通过/将过 validate_recipe 归一。"""
        if not validate_recipe(recipe):
            job.reason = (job.reason or "") + f"[{','.join(urls)}] 校验未通过\n"
            return
        dedup_key = hashlib.sha256(normalize_title(recipe["title"]).encode()).hexdigest()
        if AICollectionRepository(db).get_by_dedup_key(dedup_key):
            return
        match_scores = self._find_duplicates(db, recipe)
        self._persist_candidate(db, job, recipe, urls, dedup_key, match_scores)
        job.candidates_count += 1
        db.commit()

    def _persist_candidate(
        self, db: Session, job: IngestionJob, recipe: dict,
        urls: List[str], dedup_key: str, match_scores: dict,
    ) -> None:
        """把抽取结果落库为 review 候选 + IngestionCandidate。

        urls 为该候选参考的全部来源 URL：逐个建 RecipeSource（raw_hash 去重生效），
        主来源（第一个）写入 recipe/candidate.source_id，全部 URL 记录到 source_urls_json。
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

        ingredient_repo = IngredientRepository(db)
        for i, ing in enumerate(recipe.get("ingredients", [])):
            name = (ing.get("name") or "").strip()
            if not name:
                continue
            ingredient = ingredient_repo.get_by_name(name)
            if not ingredient:
                ingredient = Ingredient(
                    id=str(uuid.uuid4()), canonical_name=name, confidence_status="candidate"
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

    def list_models(self) -> LLMModelsResponse:
        """可用模型列表：Ollama 在线且支持文本生成的模型 + Anthropic 可选。"""
        models: List[LLMModelOption] = []
        try:
            for name in OllamaLLMProvider().list_models():
                models.append(LLMModelOption(provider="ollama", model=name, label=f"本地 {name}"))
        except LLMUnavailableError:
            pass  # Ollama 不可达，仅返回 Anthropic（如有）

        if settings.LLM_API_KEY:
            models.append(LLMModelOption(
                provider="anthropic",
                model=settings.ANTHROPIC_LLM_MODEL,
                label=f"云端 {settings.ANTHROPIC_LLM_MODEL}",
            ))

        default_provider = settings.LLM_PROVIDER
        default_model = (
            settings.ANTHROPIC_LLM_MODEL if default_provider == "anthropic" else settings.LLM_MODEL
        )
        return LLMModelsResponse(
            models=models,
            default_provider=default_provider,
            default_model=default_model,
        )

    def config_status(self) -> ConfigStatusResponse:
        llm_provider = settings.LLM_PROVIDER
        llm_configured = llm_provider == "ollama" or bool(settings.LLM_API_KEY)
        llm_model = settings.ANTHROPIC_LLM_MODEL if llm_provider == "anthropic" else settings.LLM_MODEL
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
            candidates=[self._candidate_response(db, c) for c in candidates],
        )
