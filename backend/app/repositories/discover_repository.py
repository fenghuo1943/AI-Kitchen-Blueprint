"""发现/推荐数据访问层（参考 cook DiscoverRepository）"""
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, select

from app.db.models import Recipe, Favorite, MealPlan


class DiscoverRepository:
    """发现仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_with_stats(self, household_id: str, limit: Optional[int] = None) -> List[Recipe]:
        """所有未删除菜谱（附带统计瞬态属性 _cooked_count / _is_favorited / _is_in_today_menu）"""
        cooked_sub = select(func.count(MealPlan.id)).where(
            and_(MealPlan.recipe_id == Recipe.id, MealPlan.household_id == household_id)
        ).scalar_subquery()
        fav_sub = select(func.count(Favorite.id)).where(
            and_(Favorite.recipe_id == Recipe.id, Favorite.household_id == household_id)
        ).scalar_subquery()
        today_sub = select(func.count(MealPlan.id)).where(
            and_(
                MealPlan.recipe_id == Recipe.id,
                MealPlan.household_id == household_id,
                MealPlan.target_date == date.today().isoformat(),
            )
        ).scalar_subquery()

        stmt = self.db.query(Recipe, cooked_sub.label("cooked"), fav_sub.label("fav"), today_sub.label("today")).filter(
            Recipe.deleted_at.is_(None)
        )
        if limit:
            stmt = stmt.limit(limit)
        rows = stmt.all()

        recipes = []
        for recipe, cooked, fav, today in rows:
            recipe._cooked_count = int(cooked or 0)
            recipe._is_favorited = bool(fav)
            recipe._is_in_today_menu = bool(today)
            recipes.append(recipe)
        return recipes

    def get_new_recipes(self, limit: int) -> List[Recipe]:
        """最新菜谱"""
        return self.db.query(Recipe).filter(
            Recipe.deleted_at.is_(None)
        ).order_by(Recipe.created_at.desc()).limit(limit).all()

    def get_random_recipes(self, limit: int) -> List[Recipe]:
        """随机菜谱"""
        dialect = self.db.get_bind().dialect.name
        random_expr = func.random() if dialect == "sqlite" else func.rand()
        return self.db.query(Recipe).filter(
            Recipe.deleted_at.is_(None)
        ).order_by(random_expr).limit(limit).all()
