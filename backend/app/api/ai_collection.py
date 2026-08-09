"""AI 采集入库 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.ai_collection import (
    AICollectionCreate, AICollectionJobResponse, BrowserFetchRequest,
    BrowserFetchResponse, BrowserLoginRequest, BrowserLoginResponse,
    BrowserStatusResponse, CandidateResponse, ConfigStatusResponse,
    LLMModelsResponse, PaginatedCandidateResponse,
)
from app.services.ai_collection_service import AiCollectionService
from app.services.browser_fetcher import BrowserFetchError, BrowserFetcher

router = APIRouter(prefix="/ai-collect", tags=["AI采集入库"])

# 浏览器抓取单例（Playwright）：模块级锁保证浏览器操作全局串行
_browser_fetcher = BrowserFetcher()


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


# ---------------------------------------------------------------------- #
# 浏览器抓取（Playwright，小红书等登录墙站点）
# ---------------------------------------------------------------------- #
@router.get("/browser/status", response_model=BrowserStatusResponse)
def browser_status():
    """浏览器抓取可用状态（前端手动模式提示用）。"""
    ok, reason = _browser_fetcher.available()
    return BrowserStatusResponse(
        enabled=settings.BROWSER_FETCH_ENABLED,
        available=ok,
        reason=reason,
        profile_exists=_browser_fetcher.profile_exists(),
    )


@router.post("/browser/login", response_model=BrowserLoginResponse)
def browser_login(data: BrowserLoginRequest):
    """打开有头浏览器让用户登录（登录态持久化到 profile）。阻塞到用户关闭窗口。"""
    try:
        _browser_fetcher.open_login(data.url)
    except BrowserFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BrowserLoginResponse(ok=True, message="登录完成，登录态已保存")


@router.post("/browser/fetch", response_model=BrowserFetchResponse)
def browser_fetch(data: BrowserFetchRequest):
    """用本地浏览器（复用登录态）抓取页面正文。同步，可能耗时数十秒。"""
    try:
        content = _browser_fetcher.fetch(data.url)
    except BrowserFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BrowserFetchResponse(url=data.url, content=content)
