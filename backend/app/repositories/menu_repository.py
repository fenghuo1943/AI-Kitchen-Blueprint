"""每日菜单数据访问层（参考 cook MenuRepository）"""
from datetime import date as date_cls
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, distinct

from app.db.models import (
    MealPlan, Recipe, RecipeIngredient, Ingredient,
    RecipeSeasoning, Seasoning,
)


def _to_date(value) -> date_cls:
    """字符串/date 统一转为 date 对象（SQLite 的 Date 列只接受 Python date）"""
    if isinstance(value, date_cls):
        return value
    return date_cls.fromisoformat(str(value))


class MenuRepository:
    """菜单仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def add(self, household_id: str, recipe_id: str, date: str) -> bool:
        """添加菜谱到某天（同天同菜谱去重，已存在返回 False）"""
        target = _to_date(date)
        existing = self.db.query(MealPlan.id).filter(
            and_(
                MealPlan.household_id == household_id,
                MealPlan.recipe_id == recipe_id,
                MealPlan.target_date == target,
            )
        ).first()
        if existing:
            return False
        plan = MealPlan(household_id=household_id, recipe_id=recipe_id, target_date=target)
        self.db.add(plan)
        self.db.commit()
        return True

    def remove(self, household_id: str, recipe_id: str, date: str) -> bool:
        """删除某天某菜谱"""
        target = _to_date(date)
        result = self.db.query(MealPlan).filter(
            and_(
                MealPlan.household_id == household_id,
                MealPlan.recipe_id == recipe_id,
                MealPlan.target_date == target,
            )
        ).delete()
        self.db.commit()
        return result > 0

    def get_by_date(self, household_id: str, date: str) -> List[dict]:
        """查询某天菜单"""
        target = _to_date(date)
        rows = self.db.query(MealPlan, Recipe).join(
            Recipe, Recipe.id == MealPlan.recipe_id
        ).filter(
            MealPlan.household_id == household_id,
            MealPlan.target_date == target,
            Recipe.deleted_at.is_(None),
        ).order_by(MealPlan.created_at.asc()).all()
        return [
            {
                "recipe_id": r.id,
                "title": r.title,
                "cover": r.cover,
                "cook_time": ((r.prep_minutes or 0) + (r.cook_minutes or 0)) or None,
                "added_at": p.created_at,
            }
            for p, r in rows
        ]

    def get_ingredients_by_date(self, household_id: str, date: str) -> List[dict]:
        """某天所有菜谱的食材聚合去重（采购清单）"""
        target = _to_date(date)
        rows = self.db.query(distinct(Ingredient.id), Ingredient.canonical_name).join(
            RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).join(Recipe, Recipe.id == RecipeIngredient.recipe_id).join(
            MealPlan, MealPlan.recipe_id == Recipe.id
        ).filter(
            MealPlan.household_id == household_id,
            MealPlan.target_date == target,
            Recipe.deleted_at.is_(None),
        ).order_by(Ingredient.pinyin).all()
        return [{"id": i, "name": name} for i, name in rows]

    def get_seasonings_by_date(self, household_id: str, date: str) -> List[dict]:
        """某天所有菜谱的调料聚合去重"""
        target = _to_date(date)
        rows = self.db.query(distinct(Seasoning.id), Seasoning.canonical_name).join(
            RecipeSeasoning, RecipeSeasoning.seasoning_id == Seasoning.id
        ).join(Recipe, Recipe.id == RecipeSeasoning.recipe_id).join(
            MealPlan, MealPlan.recipe_id == Recipe.id
        ).filter(
            MealPlan.household_id == household_id,
            MealPlan.target_date == target,
            Recipe.deleted_at.is_(None),
        ).order_by(Seasoning.pinyin).all()
        return [{"id": i, "name": name} for i, name in rows]

    def get_dates_by_month(self, household_id: str, month: str) -> List[str]:
        """某月有菜单的日期（用日期范围比较，兼容 SQLite/MariaDB）"""
        first = date_cls.fromisoformat(f"{month}-01")
        if first.month == 12:
            nxt = date_cls(first.year + 1, 1, 1)
        else:
            nxt = date_cls(first.year, first.month + 1, 1)
        rows = self.db.query(distinct(MealPlan.target_date)).filter(
            MealPlan.household_id == household_id,
            MealPlan.target_date >= first,
            MealPlan.target_date < nxt,
        ).order_by(MealPlan.target_date.asc()).all()
        return [d.isoformat() for (d,) in rows]

    def get_dates_paginated(self, household_id: str, page: int, page_size: int) -> List[str]:
        """分页查有菜单的日期（倒序），先分页日期再取菜谱，避免跨日期截断"""
        rows = self.db.query(distinct(MealPlan.target_date)).filter(
            MealPlan.household_id == household_id
        ).order_by(MealPlan.target_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [d.isoformat() for (d,) in rows]

    def get_by_dates(self, household_id: str, dates: List[str]) -> List[dict]:
        """查询指定日期列表下的菜谱"""
        if not dates:
            return []
        target_dates = [_to_date(d) for d in dates]
        rows = self.db.query(MealPlan.target_date, MealPlan.created_at, Recipe).join(
            Recipe, Recipe.id == MealPlan.recipe_id
        ).filter(
            MealPlan.household_id == household_id,
            MealPlan.target_date.in_(target_dates),
            Recipe.deleted_at.is_(None),
        ).order_by(MealPlan.target_date.desc(), MealPlan.created_at.asc()).all()
        return [
            {
                "date": d.isoformat(),
                "recipe_id": r.id,
                "title": r.title,
                "cover": r.cover,
                "cook_time": ((r.prep_minutes or 0) + (r.cook_minutes or 0)) or None,
                "added_at": added_at,
            }
            for d, added_at, r in rows
        ]

    def count_dates(self, household_id: str) -> int:
        """有菜单的天数"""
        return self.db.query(func.count(distinct(MealPlan.target_date))).filter(
            MealPlan.household_id == household_id
        ).scalar() or 0

    def exists_in_date(self, household_id: str, recipe_id: str, date: str) -> bool:
        """某天是否已存在该菜谱"""
        target = _to_date(date)
        return self.db.query(MealPlan.id).filter(
            and_(
                MealPlan.household_id == household_id,
                MealPlan.recipe_id == recipe_id,
                MealPlan.target_date == target,
            )
        ).first() is not None
