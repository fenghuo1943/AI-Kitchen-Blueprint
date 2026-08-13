"""浏览历史 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_resolved_household_id
from app.db.database import get_db
from app.repositories.history_repository import HistoryRepository
from app.repositories.recipe_repository import RecipeRepository
from app.services.history_service import HistoryService
from app.schemas.history import HistoryCreate, HistoryResponse, HistoryListResponse

router = APIRouter(prefix="/history", tags=["浏览历史"])


def get_history_service(db: Session = Depends(get_db)) -> HistoryService:
    """获取历史服务实例"""
    return HistoryService(HistoryRepository(db))


@router.get("", response_model=HistoryListResponse)
def list_history(
    household_id: str = Depends(get_resolved_household_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    service: HistoryService = Depends(get_history_service)
):
    """浏览历史列表（最近浏览置顶）"""
    return service.list_history(household_id, page=page, page_size=page_size)


@router.post("", response_model=HistoryResponse, status_code=201)
def record_history(
    data: HistoryCreate,
    household_id: str = Depends(get_resolved_household_id),
    db: Session = Depends(get_db),
    service: HistoryService = Depends(get_history_service)
):
    """手动记录浏览历史（详情页打开时自动记录，一般无需手动调用）"""
    recipe_repo = RecipeRepository(db)
    if not recipe_repo.get_by_id(data.recipe_id):
        raise HTTPException(status_code=404, detail="菜谱不存在")
    service.record(household_id, data.recipe_id)
    items = service.list_history(household_id, page=1, page_size=1)
    return items.data[0]


@router.delete("/{recipe_id}", status_code=204)
def delete_history_one(
    recipe_id: str,
    household_id: str = Depends(get_resolved_household_id),
    service: HistoryService = Depends(get_history_service)
):
    """删除单条浏览历史"""
    if not service.remove_one(household_id, recipe_id):
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return None


@router.delete("", status_code=204)
def clear_history(
    household_id: str = Depends(get_resolved_household_id),
    service: HistoryService = Depends(get_history_service)
):
    """清空全部浏览历史"""
    service.clear(household_id)
    return None
