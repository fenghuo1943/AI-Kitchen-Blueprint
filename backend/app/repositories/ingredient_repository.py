"""食材数据访问层"""
import json
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db.models import Ingredient, IngredientAlias, IngredientCategory, Recipe, RecipeIngredient


class IngredientRepository:
    """食材仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, ingredient_id: str) -> Optional[Ingredient]:
        """根据ID获取食材（排除已删除的）"""
        return self.db.query(Ingredient).filter(
            Ingredient.id == ingredient_id,
            Ingredient.deleted_at.is_(None)
        ).first()

    def get_by_name(self, name: str) -> Optional[Ingredient]:
        """根据标准名称获取食材"""
        return self.db.query(Ingredient).filter(Ingredient.canonical_name == name).first()

    def get_by_alias(self, alias: str) -> Optional[Ingredient]:
        """根据别名获取食材"""
        alias_obj = self.db.query(IngredientAlias).filter(IngredientAlias.alias == alias).first()
        if alias_obj:
            return self.get_by_id(alias_obj.ingredient_id)
        return None

    def search(
        self,
        query: Optional[str] = None,
        category_id: Optional[str] = None,
        allergens_exclude: Optional[List[str]] = None,
        season_month: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Ingredient], int]:
        """搜索食材"""
        stmt = self.db.query(Ingredient).filter(Ingredient.deleted_at.is_(None))

        # 关键词搜索（名称、拼音前缀）
        if query:
            search_filter = or_(
                Ingredient.canonical_name.contains(query),
                Ingredient.pinyin.like(f"{query}%")
            )
            stmt = stmt.filter(search_filter)

        # 分类筛选（分类ID）
        if category_id:
            stmt = stmt.filter(Ingredient.category_id == category_id)

        # 过敏原排除
        if allergens_exclude:
            for allergen in allergens_exclude:
                stmt = stmt.filter(~Ingredient.allergens.contains(allergen))

        # 应季月份筛选
        if season_month:
            stmt = stmt.filter(Ingredient.season_months.contains(f'"{season_month}"'))

        # 统计总数
        total = stmt.count()

        # 分页
        offset = (page - 1) * page_size
        ingredients = stmt.offset(offset).limit(page_size).all()

        return ingredients, total

    def create(self, ingredient: Ingredient) -> Ingredient:
        """创建食材"""
        self.db.add(ingredient)
        self.db.commit()
        self.db.refresh(ingredient)
        return ingredient

    def update(self, ingredient: Ingredient) -> Ingredient:
        """更新食材"""
        self.db.commit()
        self.db.refresh(ingredient)
        return ingredient

    def find_recipes_by_ingredient(self, ingredient_id: str):
        """查找使用了该食材的菜谱（排除已软删除的），返回 [(recipe_id, title), ...]"""
        return self.db.query(Recipe.id, Recipe.title).join(
            RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id
        ).filter(
            RecipeIngredient.ingredient_id == ingredient_id,
            Recipe.deleted_at.is_(None)
        ).all()

    def soft_delete(self, ingredient_id: str) -> bool:
        """软删除食材"""
        ingredient = self.get_by_id(ingredient_id)
        if not ingredient:
            return False
        from datetime import datetime
        ingredient.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def add_alias(self, alias: IngredientAlias) -> IngredientAlias:
        """添加食材别名"""
        self.db.add(alias)
        self.db.commit()
        self.db.refresh(alias)
        return alias

    def remove_alias(self, alias_id: str) -> bool:
        """删除食材别名"""
        alias = self.db.query(IngredientAlias).filter(IngredientAlias.id == alias_id).first()
        if not alias:
            return False
        self.db.delete(alias)
        self.db.commit()
        return True

    def get_aliases(self, ingredient_id: str) -> List[IngredientAlias]:
        """获取食材的所有别名"""
        return self.db.query(IngredientAlias).filter(
            IngredientAlias.ingredient_id == ingredient_id
        ).all()

    def check_alias_exists(self, alias: str, exclude_id: Optional[str] = None) -> bool:
        """检查别名是否已存在"""
        stmt = self.db.query(IngredientAlias).filter(IngredientAlias.alias == alias)
        if exclude_id:
            stmt = stmt.filter(IngredientAlias.id != exclude_id)
        return stmt.count() > 0

    def get_category_name(self, category_id: Optional[str]) -> Optional[str]:
        """获取食材分类名称"""
        if not category_id:
            return None
        cat = self.db.query(IngredientCategory).filter(IngredientCategory.id == category_id).first()
        return cat.name if cat else None
