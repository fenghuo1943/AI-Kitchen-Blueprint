"""菜谱数据访问层"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models import (
    Recipe, RecipeIngredient, RecipeStep, RecipeTag, Tag
)


class RecipeRepository:
    """菜谱仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, recipe_id: str) -> Optional[Recipe]:
        """根据ID获取菜谱"""
        return self.db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.deleted_at.is_(None)
        ).first()

    def search(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        difficulty: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_cook_time: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Recipe], int]:
        """搜索菜谱"""
        stmt = self.db.query(Recipe).filter(Recipe.deleted_at.is_(None))

        # 关键词搜索
        if query:
            search_filter = or_(
                Recipe.title.contains(query),
                Recipe.summary.contains(query)
            )
            stmt = stmt.filter(search_filter)

        # 状态筛选
        if status:
            stmt = stmt.filter(Recipe.status == status)

        # 难度筛选
        if difficulty:
            stmt = stmt.filter(Recipe.difficulty == difficulty)

        # 最大烹饪时间
        if max_cook_time is not None:
            stmt = stmt.filter(
                (Recipe.cook_minutes + Recipe.prep_minutes) <= max_cook_time
            )

        # 标签筛选
        if tags:
            stmt = stmt.join(RecipeTag).join(Tag).filter(Tag.name.in_(tags))

        # 统计总数
        total = stmt.count()

        # 分页
        offset = (page - 1) * page_size
        recipes = stmt.offset(offset).limit(page_size).all()

        return recipes, total

    def create(self, recipe: Recipe) -> Recipe:
        """创建菜谱"""
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def update(self, recipe: Recipe) -> Recipe:
        """更新菜谱"""
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def soft_delete(self, recipe_id: str) -> bool:
        """软删除菜谱"""
        recipe = self.get_by_id(recipe_id)
        if not recipe:
            return False
        from datetime import datetime
        recipe.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def add_ingredient(self, recipe_ingredient: RecipeIngredient) -> RecipeIngredient:
        """添加菜谱食材"""
        self.db.add(recipe_ingredient)
        self.db.commit()
        self.db.refresh(recipe_ingredient)
        return recipe_ingredient

    def remove_ingredients(self, recipe_id: str) -> None:
        """删除菜谱的所有食材"""
        self.db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def get_ingredients(self, recipe_id: str) -> List[RecipeIngredient]:
        """获取菜谱食材"""
        return self.db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).order_by(RecipeIngredient.sort_order).all()

    def add_step(self, recipe_step: RecipeStep) -> RecipeStep:
        """添加菜谱步骤"""
        self.db.add(recipe_step)
        self.db.commit()
        self.db.refresh(recipe_step)
        return recipe_step

    def remove_steps(self, recipe_id: str) -> None:
        """删除菜谱的所有步骤"""
        self.db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def get_steps(self, recipe_id: str) -> List[RecipeStep]:
        """获取菜谱步骤"""
        return self.db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).order_by(RecipeStep.step_no).all()

    def add_tags(self, recipe_id: str, tag_names: List[str]) -> None:
        """添加菜谱标签"""
        for tag_name in tag_names:
            # 查找或创建标签
            tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, type="cuisine")
                self.db.add(tag)
                self.db.flush()

            # 创建关联
            recipe_tag = RecipeTag(recipe_id=recipe_id, tag_id=tag.id)
            self.db.add(recipe_tag)
        self.db.commit()

    def remove_tags(self, recipe_id: str) -> None:
        """删除菜谱的所有标签"""
        self.db.query(RecipeTag).filter(
            RecipeTag.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def get_tags(self, recipe_id: str) -> List[Tag]:
        """获取菜谱标签"""
        return self.db.query(Tag).join(RecipeTag).filter(
            RecipeTag.recipe_id == recipe_id
        ).all()

    def publish_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """发布菜谱"""
        recipe = self.get_by_id(recipe_id)
        if not recipe:
            return None

        from datetime import datetime
        recipe.status = "published"
        recipe.revision += 1
        recipe.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(recipe)
        return recipe
