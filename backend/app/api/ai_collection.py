"""AI 采集入库 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.ai_collection import (
    AICollectionCreate, AICollectionJobResponse, CandidateResponse,
    ConfigStatusResponse, LLMModelsResponse, PaginatedCandidateResponse,
)
from app.services.ai_collection_service import AiCollectionService

router = APIRouter(prefix="/ai-collect", tags=["AI采集入库"])


@router.post("/jobs", response_model=AICollectionJobResponse, status_code=201)
def create_ai_job(data: AICollectionCreate, db: Session = Depends(get_db)):
    """提交 AI 采集任务（搜索→LLM 抽取→待审候选）。"""
    try:
        return AiCollectionService().create_ai_job(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}", response_model=AICollectionJobResponse)
def get_ai_job(job_id: str, db: Session = Depends(get_db)):
    """轮询采集任务与候选列表。"""
    result = AiCollectionService().get_job_detail(db, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="采集任务不存在")
    return result


@router.get("/candidates", response_model=PaginatedCandidateResponse)
def list_candidates(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """全局待审队列。"""
    return AiCollectionService().list_pending(db, page, page_size)


@router.post("/candidates/{candidate_id}/approve", response_model=CandidateResponse)
def approve_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """确认候选：new=发布并触发索引；merge=合入目标菜谱。"""
    try:
        result = AiCollectionService().review_candidate(db, candidate_id, "approve")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="候选不存在")
    return result


@router.post("/candidates/{candidate_id}/reject", response_model=CandidateResponse)
def reject_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """拒绝候选（软删）。"""
    try:
        result = AiCollectionService().review_candidate(db, candidate_id, "reject")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="候选不存在")
    return result


@router.get("/config/status", response_model=ConfigStatusResponse)
def config_status():
    """Tavily / LLM 配置状态（前端横幅用）。"""
    return AiCollectionService().config_status()


@router.get("/models", response_model=LLMModelsResponse)
def list_models():
    """可用 LLM 模型列表（Ollama 在线模型 + 可选 Anthropic/DeepSeek/OpenRouter/通用端点）与默认选择。"""
    return AiCollectionService().list_models()
