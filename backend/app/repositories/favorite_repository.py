"""收藏数据访问层"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.db.models import Favorite, Recipe


class FavoriteRepository:
    """收藏仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_household(self, household_id: str, offset: int = 0, limit: int = 30) -> List[dict]:
        """收藏列表（关联菜谱标题，按收藏时间倒序，仅展示未删除菜谱）"""
        rows = self.db.query(Favorite, Recipe.title, Recipe.cover).join(
            Recipe, Recipe.id == Favorite.recipe_id
        ).filter(
            Favorite.household_id == household_id,
            Recipe.deleted_at.is_(None),
        ).order_by(Favorite.created_at.desc()).offset(offset).limit(limit).all()
        return [
            {"id": f.id, "recipe_id": f.recipe_id, "recipe_title": title, "cover": cover, "created_at": f.created_at}
            for f, title, cover in rows
        ]

    def count_by_household(self, household_id: str) -> int:
        """收藏总数（与列表一致，仅统计未删除菜谱）"""
        return self.db.query(func.count(Favorite.id)).join(
            Recipe, Recipe.id == Favorite.recipe_id
        ).filter(
            Favorite.household_id == household_id,
            Recipe.deleted_at.is_(None),
        ).scalar() or 0

    def is_favorite(self, household_id: str, recipe_id: str) -> bool:
        """是否已收藏"""
        return self.db.query(Favorite.id).filter(
            and_(Favorite.household_id == household_id, Favorite.recipe_id == recipe_id)
        ).first() is not None

    def add(self, household_id: str, recipe_id: str) -> Optional[Favorite]:
        """收藏（幂等：已存在则返回 None）"""
        if self.is_favorite(household_id, recipe_id):
            return None
        favorite = Favorite(household_id=household_id, recipe_id=recipe_id)
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)
        return favorite

    def delete(self, household_id: str, recipe_id: str) -> bool:
        """取消收藏"""
        result = self.db.query(Favorite).filter(
            and_(Favorite.household_id == household_id, Favorite.recipe_id == recipe_id)
        ).delete()
        self.db.commit()
        return result > 0
