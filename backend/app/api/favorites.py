"""收藏 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.favorite_repository import FavoriteRepository
from app.repositories.recipe_repository import RecipeRepository
from app.services.favorite_service import FavoriteService
from app.schemas.favorite import FavoriteCreate, FavoriteResponse, FavoriteListResponse

router = APIRouter(prefix="/favorites", tags=["收藏"])


def get_favorite_service(db: Session = Depends(get_db)) -> FavoriteService:
    """获取收藏服务实例"""
    return FavoriteService(FavoriteRepository(db))


@router.get("", response_model=FavoriteListResponse)
def list_favorites(
    household_id: str = Query(..., description="家庭ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    service: FavoriteService = Depends(get_favorite_service)
):
    """收藏列表"""
    return service.list_favorites(household_id, page=page, page_size=page_size)


@router.post("", response_model=FavoriteResponse, status_code=201)
def add_favorite(
    data: FavoriteCreate,
    household_id: str = Query(..., description="家庭ID"),
    db: Session = Depends(get_db),
    service: FavoriteService = Depends(get_favorite_service)
):
    """收藏菜谱（幂等）"""
    # 校验菜谱存在
    recipe_repo = RecipeRepository(db)
    if not recipe_repo.get_by_id(data.recipe_id):
        raise HTTPException(status_code=404, detail="菜谱不存在")
    result = service.add_favorite(household_id, data.recipe_id)
    if not result:
        # 已收藏过：返回现有收藏，不报错（幂等）
        existing = service.list_favorites(household_id, page=1, page_size=100)
        for item in existing.data:
            if item.recipe_id == data.recipe_id:
                return item
        raise HTTPException(status_code=409, detail="已收藏")
    return result


@router.delete("/{recipe_id}", status_code=204)
def remove_favorite(
    recipe_id: str,
    household_id: str = Query(..., description="家庭ID"),
    service: FavoriteService = Depends(get_favorite_service)
):
    """取消收藏"""
    if not service.remove_favorite(household_id, recipe_id):
        raise HTTPException(status_code=404, detail="未找到收藏记录")
    return None
