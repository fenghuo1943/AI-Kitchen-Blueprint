"""菜谱业务逻辑层"""
import uuid
from typing import Optional, List
from datetime import datetime

from app.db.models import Recipe, RecipeIngredient, RecipeStep
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeResponse,
    RecipeListResponse, RecipeSearchRequest,
    RecipeIngredientResponse, RecipeStepResponse, RecipeTagResponse
)


class RecipeService:
    """菜谱服务类"""

    def __init__(
        self,
        recipe_repository: RecipeRepository,
        ingredient_repository: IngredientRepository
    ):
        self.recipe_repository = recipe_repository
        self.ingredient_repository = ingredient_repository

    def get_recipe(self, recipe_id: str) -> Optional[RecipeResponse]:
        """获取菜谱详情"""
        recipe = self.recipe_repository.get_by_id(recipe_id)
        if not recipe:
            return None
        return self._to_response(recipe)

    def search_recipes(self, request: RecipeSearchRequest, page: int = 1, page_size: int = 20) -> RecipeListResponse:
        """搜索菜谱"""
        recipes, total = self.recipe_repository.search(
            query=request.query,
            status=request.status,
            difficulty=request.difficulty,
            tags=request.tags,
            max_cook_time=request.max_cook_time,
            page=page,
            page_size=page_size
        )
        return RecipeListResponse(
            data=[self._to_response(r) for r in recipes],
            total=total,
            page=page,
            page_size=page_size
        )

    def create_recipe(self, data: RecipeCreate, created_by: Optional[str] = None) -> RecipeResponse:
        """创建菜谱"""
        # 创建菜谱
        recipe = Recipe(
            id=str(uuid.uuid4()),
            title=data.title,
            summary=data.summary,
            servings=data.servings,
            prep_minutes=data.prep_minutes,
            cook_minutes=data.cook_minutes,
            difficulty=data.difficulty,
            source_id=data.source_id,
            status="draft",
            revision=1,
            created_by=created_by
        )
        recipe = self.recipe_repository.create(recipe)

        # 添加食材
        for ingredient_data in data.ingredients:
            recipe_ingredient = RecipeIngredient(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                ingredient_id=ingredient_data.ingredient_id,
                quantity=ingredient_data.quantity,
                unit=ingredient_data.unit,
                raw_quantity=ingredient_data.raw_quantity,
                preparation=ingredient_data.preparation,
                optional=1 if ingredient_data.optional else 0,
                sort_order=ingredient_data.sort_order
            )
            self.recipe_repository.add_ingredient(recipe_ingredient)

        # 添加步骤
        for step_data in data.steps:
            recipe_step = RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                step_no=step_data.step_no,
                instruction=step_data.instruction,
                duration_minutes=step_data.duration_minutes,
                image_url=step_data.image_url
            )
            self.recipe_repository.add_step(recipe_step)

        # 添加标签
        if data.tags:
            self.recipe_repository.add_tags(recipe.id, data.tags)

        return self._to_response(recipe)

    def update_recipe(self, recipe_id: str, data: RecipeUpdate) -> Optional[RecipeResponse]:
        """更新菜谱"""
        recipe = self.recipe_repository.get_by_id(recipe_id)
        if not recipe:
            return None

        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(recipe, key, value)

        recipe.updated_at = datetime.utcnow()
        recipe = self.recipe_repository.update(recipe)

        return self._to_response(recipe)

    def delete_recipe(self, recipe_id: str) -> bool:
        """删除菜谱（软删除）"""
        return self.recipe_repository.soft_delete(recipe_id)

    def publish_recipe(self, recipe_id: str) -> Optional[RecipeResponse]:
        """发布菜谱"""
        recipe = self.recipe_repository.publish_recipe(recipe_id)
        if not recipe:
            return None
        return self._to_response(recipe)

    def _to_response(self, recipe: Recipe) -> RecipeResponse:
        """将数据库模型转换为响应模式"""
        # 获取食材
        recipe_ingredients = self.recipe_repository.get_ingredients(recipe.id)
        ingredients = []
        for ri in recipe_ingredients:
            ingredient = self.ingredient_repository.get_by_id(ri.ingredient_id)
            ingredients.append(RecipeIngredientResponse(
                id=ri.id,
                ingredient_id=ri.ingredient_id,
                ingredient_name=ingredient.canonical_name if ingredient else "未知",
                quantity=ri.quantity,
                unit=ri.unit,
                preparation=ri.preparation,
                optional=bool(ri.optional),
                sort_order=ri.sort_order
            ))

        # 获取步骤
        recipe_steps = self.recipe_repository.get_steps(recipe.id)
        steps = [
            RecipeStepResponse(
                id=s.id,
                step_no=s.step_no,
                instruction=s.instruction,
                duration_minutes=s.duration_minutes,
                image_url=s.image_url
            )
            for s in recipe_steps
        ]

        # 获取标签
        tags = self.recipe_repository.get_tags(recipe.id)
        tag_responses = [
            RecipeTagResponse(id=t.id, name=t.name, type=t.type)
            for t in tags
        ]

        return RecipeResponse(
            id=recipe.id,
            title=recipe.title,
            summary=recipe.summary,
            servings=recipe.servings,
            prep_minutes=recipe.prep_minutes,
            cook_minutes=recipe.cook_minutes,
            difficulty=recipe.difficulty,
            source_id=recipe.source_id,
            status=recipe.status,
            revision=recipe.revision,
            created_by=recipe.created_by,
            ingredients=ingredients,
            steps=steps,
            tags=tag_responses,
            created_at=recipe.created_at,
            updated_at=recipe.updated_at
        )
