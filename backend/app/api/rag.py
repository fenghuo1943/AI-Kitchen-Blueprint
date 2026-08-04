"""RAG 语义检索与索引管理接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.rag.retriever import HybridRetriever
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.recipe_repository import RecipeRepository
from app.schemas.rag import IndexStatusResponse, RagSearchRequest, RagSearchResponse
from app.tasks import executor

router = APIRouter(prefix="/rag", tags=["语义检索"])


@router.post("/search", response_model=RagSearchResponse)
def rag_search(req: RagSearchRequest, db: Session = Depends(get_db)):
    """语义检索：结构化硬约束过滤 → 向量召回 → 混合重排，返回 Top N 菜谱候选。

    引擎（Ollama/Chroma）不可用时返回 200 + engine_available=False + 可读 error，
    不影响其他接口（RAG 规范：模型不可用不中断核心功能）。
    """
    result = HybridRetriever().retrieve(
        db,
        req.query,
        filters={
            "max_cook_time": req.max_cook_time,
            "tags": req.tags,
            "ingredient_ids": req.ingredient_ids,
            "category_id": req.category_id,
            "household_id": req.household_id,
        },
        rerank_top_k=req.top_k or settings.RERANK_TOP_K,
    )
    return RagSearchResponse(
        results=[
            {
                "recipe_id": h.recipe_id,
                "title": h.title,
                "cover": h.cover,
                "summary": h.summary,
                "score": h.score,
                "matched_ingredients": h.matched_ingredients,
                "reasons": h.reasons,
                "chunks": h.chunks,
            }
            for h in result.hits
        ],
        total=result.total,
        engine_available=result.engine_available,
        took_ms=result.took_ms,
        error=result.error,
    )


# 注意路由顺序：静态路径需先于动态 /index/{recipe_id} 注册
@router.post("/index/rebuild")
def enqueue_rebuild():
    """全量重建索引（后台异步，单飞）。"""
    executor.enqueue_rebuild()
    return {"status": "queued", "task": "rebuild"}


@router.get("/index/status", response_model=IndexStatusResponse)
def index_status(db: Session = Depends(get_db)):
    """索引状态：已索引/已发布菜谱数、后台任务观测、各类型块数。"""
    doc_repo = DocumentChunkRepository(db)
    recipe_repo = RecipeRepository(db)
    snap = executor.snapshot()
    return IndexStatusResponse(
        indexed_count=len(doc_repo.indexed_recipe_ids()),
        published_count=len(recipe_repo.list_published_ids()),
        last_rebuild_at=snap["last_rebuild_at"],
        running=snap["running"],
        queued=snap["queued"],
        failed=snap["failed"],
        last_error=snap["last_error"],
        breakdown_by_type=doc_repo.count_by_type(),
    )


@router.post("/index/{recipe_id}")
def enqueue_index(recipe_id: str):
    """强制（重）建单道菜索引（后台异步，幂等）。"""
    executor.enqueue_index(recipe_id)
    return {"status": "queued", "recipe_id": recipe_id}
