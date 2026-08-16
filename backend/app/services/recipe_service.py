"""菜谱业务逻辑层"""
import uuid
from typing import Optional, List
from datetime import datetime

from app.core.category_classifier import resolve_recipe_categories
from app.core.pinyin import to_pinyin
from app.db.models import Recipe, RecipeIngredient, RecipeStep
from app.repositories.category_repository import get_default_category_id, resolve_category_id
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.tasks.executor import enqueue_index, enqueue_delete
from app.schemas.batch import BatchDeleteFailure, BatchDeleteResponse
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeResponse,
    RecipeListResponse, RecipeIngredientResponse, RecipeStepResponse,
    RecipeTagResponse, RecipeSeasoningResponse, RecipeCategoryItemResponse,
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

    def get_recipe(self, recipe_id: str, household_id: Optional[str] = None,
                   record_history: bool = True) -> Optional[RecipeResponse]:
        """获取菜谱详情（可选记录浏览历史）"""
        recipe = self.recipe_repository.get_by_id(recipe_id)
        if not recipe:
            return None
        if household_id and record_history:
            self.recipe_repository.record_history(household_id, recipe_id)
        return self._to_response(recipe, household_id=household_id)

    def search_recipes(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        difficulty: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_cook_time: Optional[int] = None,
        ingredients: Optional[List[str]] = None,
        match: str = "any",
        category_id: Optional[str] = None,
        household_id: Optional[str] = None,
        sort: str = "score",
        order: str = "desc",
        deleted: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> RecipeListResponse:
        """搜索菜谱"""
        recipes, total = self.recipe_repository.search(
            query=query,
            status=status,
            difficulty=difficulty,
            tags=tags,
            max_cook_time=max_cook_time,
            ingredient_ids=ingredients,
            match_mode=match,
            category_id=category_id,
            household_id=household_id,
            sort=sort,
            order=order,
            deleted=deleted,
            page=page,
            page_size=page_size,
        )
        return RecipeListResponse(
            data=[self._to_response(r, household_id=household_id) for r in recipes],
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
            pinyin=to_pinyin(data.title),
            summary=data.summary,
            cover=data.cover,
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

        self._save_relations(recipe.id, data.ingredients, data.steps, data.tags,
                             data.category_ids, data.seasonings)

        return self._to_response(recipe)

    def update_recipe(self, recipe_id: str, data: RecipeUpdate) -> Optional[RecipeResponse]:
        """更新菜谱（支持食材/步骤/调料/分类/标签完整更新，删了重建）"""
        recipe = self.recipe_repository.get_by_id(recipe_id)
        if not recipe:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 顶层字段更新
        for key in ("title", "summary", "cover", "servings", "prep_minutes",
                    "cook_minutes", "difficulty", "status"):
            if key in update_data:
                setattr(recipe, key, update_data[key])
        if "title" in update_data and update_data["title"]:
            recipe.pinyin = to_pinyin(update_data["title"])

        recipe.updated_at = datetime.utcnow()
        self.recipe_repository.update(recipe)

        # 关联数据：删了重建（update_data 中为 dict）
        if "ingredients" in update_data:
            self.recipe_repository.remove_ingredients(recipe_id)
            for ing in update_data["ingredients"]:
                self.recipe_repository.add_ingredient(RecipeIngredient(
                    id=str(uuid.uuid4()),
                    recipe_id=recipe_id,
                    ingredient_id=ing["ingredient_id"],
                    quantity=ing.get("quantity"),
                    unit=ing.get("unit"),
                    raw_quantity=ing.get("raw_quantity"),
                    preparation=ing.get("preparation"),
                    optional=1 if ing.get("optional") else 0,
                    sort_order=ing.get("sort_order", 0),
                ))
        if "steps" in update_data:
            self.recipe_repository.remove_steps(recipe_id)
            for step in update_data["steps"]:
                self.recipe_repository.add_step(RecipeStep(
                    id=str(uuid.uuid4()),
                    recipe_id=recipe_id,
                    step_no=step["step_no"],
                    instruction=step["instruction"],
                    duration_minutes=step.get("duration_minutes"),
                    image_url=step.get("image_url"),
                ))
        if "tags" in update_data:
            self.recipe_repository.remove_tags(recipe_id)
            if update_data["tags"]:
                self.recipe_repository.add_tags(recipe_id, update_data["tags"])
        if "category_ids" in update_data:
            self.recipe_repository.remove_categories(recipe_id)
            cids = list(update_data["category_ids"] or [])
            if not cids:  # 清空分类时落到默认分类（与入库规则一致）
                cids = [get_default_category_id(self.recipe_repository.db, "recipe")]
            for cid in cids:
                self.recipe_repository.add_category(recipe_id, cid)
        if "seasonings" in update_data:
            self.recipe_repository.remove_seasonings(recipe_id)
            for s in update_data["seasonings"]:
                self.recipe_repository.add_seasoning(recipe_id, s["seasoning_id"], s.get("quantity"))

        recipe = self.recipe_repository.get_by_id(recipe_id)
        # PATCH 可直接改 status：转 published 建索引，转 archived 清索引
        if recipe.status == "published":
            enqueue_index(recipe_id)
        elif recipe.status == "archived":
            enqueue_delete(recipe_id)
        return self._to_response(recipe)

    def delete_recipe(self, recipe_id: str) -> bool:
        """删除菜谱（软删除，进入回收站）"""
        ok = self.recipe_repository.soft_delete(recipe_id)
        if ok:
            enqueue_delete(recipe_id)
        return ok

    def hard_delete_recipe(self, recipe_id: str) -> bool:
        """彻底删除菜谱（回收站内，级联清理）"""
        ok = self.recipe_repository.hard_delete(recipe_id)
        if ok:
            enqueue_delete(recipe_id)
        return ok

    def hard_delete_many(self, ids: List[str]) -> BatchDeleteResponse:
        """批量彻底删除回收站中的菜谱（尽力而为，逐条复用单删逻辑做级联清理）"""
        ids = list(dict.fromkeys(ids))  # 去重，避免重复 id 重复计数
        deleted_count = 0
        failed: List[BatchDeleteFailure] = []
        for recipe_id in ids:
            recipe = self.recipe_repository.get_by_id_any(recipe_id)
            if not recipe:
                # 已不存在（如已被并发删除），视为已删除
                deleted_count += 1
                continue
            if self.recipe_repository.hard_delete(recipe_id):
                deleted_count += 1
                enqueue_delete(recipe_id)
        return BatchDeleteResponse(deleted_count=deleted_count, failed=failed)

    def restore_recipe(self, recipe_id: str) -> Optional[RecipeResponse]:
        """恢复软删除的菜谱"""
        recipe = self.recipe_repository.restore(recipe_id)
        if not recipe:
            return None
        # 恢复后若为已发布状态则重新入索引（软删时索引已被清）
        if recipe.status == "published":
            enqueue_index(recipe_id)
        return self._to_response(recipe)

    def publish_recipe(self, recipe_id: str) -> Optional[RecipeResponse]:
        """发布菜谱"""
        recipe = self.recipe_repository.publish_recipe(recipe_id)
        if not recipe:
            return None
        enqueue_index(recipe_id)
        return self._to_response(recipe)

    def _save_relations(self, recipe_id: str, ingredients, steps, tags,
                        category_ids: List[str], seasonings) -> None:
        """新增菜谱时保存关联数据"""
        for ingredient_data in ingredients:
            recipe_ingredient = RecipeIngredient(
                id=str(uuid.uuid4()),
                recipe_id=recipe_id,
                ingredient_id=ingredient_data.ingredient_id,
                quantity=ingredient_data.quantity,
                unit=ingredient_data.unit,
                raw_quantity=ingredient_data.raw_quantity,
                preparation=ingredient_data.preparation,
                optional=1 if ingredient_data.optional else 0,
                sort_order=ingredient_data.sort_order
            )
            self.recipe_repository.add_ingredient(recipe_ingredient)

        for step_data in steps:
            recipe_step = RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=recipe_id,
                step_no=step_data.step_no,
                instruction=step_data.instruction,
                duration_minutes=step_data.duration_minutes,
                image_url=step_data.image_url
            )
            self.recipe_repository.add_step(recipe_step)

        if tags:
            self.recipe_repository.add_tags(recipe_id, tags)

        category_ids = list(category_ids or [])
        if not category_ids:  # 未指定分类时按标题自动分类；蔬菜/肉类按主食材自动补挂（入库规则；未识别回落默认）
            recipe = self.recipe_repository.get_by_id(recipe_id)
            title = recipe.title if recipe else None
            ingredient_names = []
            for ing_data in ingredients:
                ing_obj = self.ingredient_repository.get_by_id(ing_data.ingredient_id)
                if ing_obj:
                    ingredient_names.append(ing_obj.canonical_name)
            category_ids = [
                resolve_category_id(self.recipe_repository.db, "recipe", name=n)
                for n in resolve_recipe_categories(title, None, ingredient_names)
            ]
        for cid in category_ids:
            self.recipe_repository.add_category(recipe_id, cid)

        for s in seasonings:
            self.recipe_repository.add_seasoning(recipe_id, s.seasoning_id, s.quantity)

    def _to_response(self, recipe: Recipe, household_id: Optional[str] = None) -> RecipeResponse:
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

        # 获取调料
        seasonings = [
            RecipeSeasoningResponse(**s)
            for s in self.recipe_repository.get_seasonings_detail(recipe.id)
        ]

        # 获取分类
        categories = [
            RecipeCategoryItemResponse(id=c.id, name=c.name)
            for c in self.recipe_repository.get_categories(recipe.id)
        ]

        # 用户相关状态（优先读取列表搜索时设置的瞬态属性，避免重复查询）
        is_favorited = bool(getattr(recipe, "_is_favorited", False))
        is_in_today_menu = bool(getattr(recipe, "_is_in_today_menu", False))
        cooked_count = int(getattr(recipe, "_cooked_count", 0))
        if household_id and not hasattr(recipe, "_is_favorited"):
            is_favorited = self.recipe_repository.is_favorited(household_id, recipe.id)
            is_in_today_menu = self.recipe_repository.is_in_today_menu(household_id, recipe.id)
            cooked_count = self.recipe_repository.cooked_count(household_id, recipe.id)

        return RecipeResponse(
            id=recipe.id,
            title=recipe.title,
            pinyin=recipe.pinyin,
            summary=recipe.summary,
            cover=recipe.cover,
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
            seasonings=seasonings,
            categories=categories,
            is_favorited=is_favorited,
            is_in_today_menu=is_in_today_menu,
            cooked_count=cooked_count,
            deleted_at=recipe.deleted_at,
            created_at=recipe.created_at,
            updated_at=recipe.updated_at
        )
