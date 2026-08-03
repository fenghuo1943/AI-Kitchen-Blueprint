"""浏览历史数据访问层"""
from typing import List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import RecipeHistory, Recipe


class HistoryRepository:
    """浏览历史仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_household(self, household_id: str, offset: int = 0, limit: int = 30) -> List[dict]:
        """历史列表（按 viewed_at 倒序，每菜谱一条，最近浏览置顶）"""
        rows = self.db.query(RecipeHistory, Recipe.title, Recipe.cover).join(
            Recipe, Recipe.id == RecipeHistory.recipe_id
        ).filter(
            RecipeHistory.household_id == household_id,
            Recipe.deleted_at.is_(None),
        ).order_by(RecipeHistory.viewed_at.desc()).offset(offset).limit(limit).all()
        return [
            {"id": h.id, "recipe_id": h.recipe_id, "recipe_title": title, "cover": cover, "viewed_at": h.viewed_at}
            for h, title, cover in rows
        ]

    def count_by_household(self, household_id: str) -> int:
        """历史总数"""
        return self.db.query(RecipeHistory.id).filter(
            RecipeHistory.household_id == household_id
        ).count()

    def record(self, household_id: str, recipe_id: str) -> None:
        """记录历史（upsert：已存在则刷新 viewed_at，保证每菜谱一条）"""
        history = self.db.query(RecipeHistory).filter(
            and_(RecipeHistory.household_id == household_id, RecipeHistory.recipe_id == recipe_id)
        ).first()
        now = datetime.utcnow()
        if history:
            history.viewed_at = now
            history.updated_at = now
        else:
            history = RecipeHistory(
                household_id=household_id,
                recipe_id=recipe_id,
                viewed_at=now,
            )
            self.db.add(history)
        self.db.commit()

    def delete_one(self, household_id: str, recipe_id: str) -> bool:
        """删除单条历史"""
        result = self.db.query(RecipeHistory).filter(
            and_(RecipeHistory.household_id == household_id, RecipeHistory.recipe_id == recipe_id)
        ).delete()
        self.db.commit()
        return result > 0

    def clear(self, household_id: str) -> int:
        """清空某家庭全部历史"""
        result = self.db.query(RecipeHistory).filter(
            RecipeHistory.household_id == household_id
        ).delete()
        self.db.commit()
        return result
