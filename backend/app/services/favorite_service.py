"""收藏业务逻辑层"""
from typing import Optional

from app.repositories.favorite_repository import FavoriteRepository
from app.schemas.favorite import FavoriteResponse, FavoriteListResponse


class FavoriteService:
    """收藏服务类"""

    def __init__(self, repository: FavoriteRepository):
        self.repository = repository

    def list_favorites(self, household_id: str, page: int = 1, page_size: int = 30) -> FavoriteListResponse:
        """收藏列表"""
        offset = (page - 1) * page_size
        items = self.repository.get_by_household(household_id, offset, page_size)
        total = self.repository.count_by_household(household_id)
        return FavoriteListResponse(
            data=[FavoriteResponse(**item) for item in items],
            total=total, page=page, page_size=page_size
        )

    def add_favorite(self, household_id: str, recipe_id: str) -> Optional[FavoriteResponse]:
        """收藏（幂等）"""
        favorite = self.repository.add(household_id, recipe_id)
        if not favorite:
            return None
        return FavoriteResponse(
            id=favorite.id,
            recipe_id=favorite.recipe_id,
            recipe_title="",
            cover=None,
            created_at=favorite.created_at,
        )

    def remove_favorite(self, household_id: str, recipe_id: str) -> bool:
        """取消收藏"""
        return self.repository.delete(household_id, recipe_id)
