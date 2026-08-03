"""发现/推荐 API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.discover_repository import DiscoverRepository
from app.services.discover_service import DiscoverService
from app.schemas.discover import DiscoverResponse

router = APIRouter(prefix="/discover", tags=["发现"])


def get_discover_service(db: Session = Depends(get_db)) -> DiscoverService:
    """获取发现服务实例"""
    return DiscoverService(DiscoverRepository(db))


@router.get("", response_model=DiscoverResponse)
def discover(
    type_: str = Query("today", alias="type", pattern="^(today|hot|new|random)$", description="推荐类型"),
    household_id: str = Query("", description="家庭ID（用于今日推荐/热门排序）"),
    limit: int = Query(6, ge=1, le=50),
    service: DiscoverService = Depends(get_discover_service)
):
    """发现/推荐：today=今日推荐 hot=热门 new=最新 random=随机"""
    if type_ == "hot":
        return service.hot_recipes(household_id or None, limit)
    if type_ == "new":
        return service.new_recipes(limit)
    if type_ == "random":
        return service.random_recipes(limit)
    return service.today_recommend(household_id or None, limit)
