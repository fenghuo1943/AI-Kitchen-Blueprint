"""食材业务逻辑层"""
import json
import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.core.category_classifier import classify_ingredient
from app.core.pinyin import to_pinyin
from app.db.models import Ingredient, IngredientAlias
from app.repositories.category_repository import DEFAULT_CATEGORY_NAME, get_default_category_id, get_or_create_category_id
from app.repositories.ingredient_repository import IngredientRepository
from app.schemas.ingredient import (
    IngredientCreate, IngredientUpdate, IngredientResponse,
    IngredientListResponse, IngredientSearchRequest
)


class IngredientService:
    """食材服务类"""

    def __init__(self, repository: IngredientRepository):
        self.repository = repository

    def get_ingredient(self, ingredient_id: str) -> Optional[IngredientResponse]:
        """获取食材详情"""
        ingredient = self.repository.get_by_id(ingredient_id)
        if not ingredient:
            return None
        return self._to_response(ingredient)

    def search_ingredients(self, request: IngredientSearchRequest, page: int = 1, page_size: int = 20) -> IngredientListResponse:
        """搜索食材"""
        ingredients, total = self.repository.search(
            query=request.query,
            category_id=request.category_id,
            allergens_exclude=request.allergens_exclude,
            season_month=request.season_month,
            page=page,
            page_size=page_size
        )
        return IngredientListResponse(
            data=[self._to_response(i) for i in ingredients],
            total=total,
            page=page,
            page_size=page_size
        )

    def create_ingredient(self, data: IngredientCreate) -> IngredientResponse:
        """创建食材"""
        # 检查名称是否已存在
        existing = self.repository.get_by_name(data.canonical_name)
        if existing:
            raise ValueError(f"食材名称 '{data.canonical_name}' 已存在")

        # 未指定分类时按名称自动分类（未识别回落默认）
        category_id = data.category_id
        if not category_id:
            cat_name = classify_ingredient(data.canonical_name) or DEFAULT_CATEGORY_NAME
            category_id = get_or_create_category_id(self.repository.db, "ingredient", cat_name)

        # 创建食材
        ingredient = Ingredient(
            id=str(uuid.uuid4()),
            canonical_name=data.canonical_name,
            pinyin=to_pinyin(data.canonical_name),
            category_id=category_id,
            season_months=json.dumps(data.season_months) if data.season_months else None,
            allergens=json.dumps(data.allergens) if data.allergens else None,
            nutrition_ref=data.nutrition_ref,
            confidence_status=data.confidence_status
        )
        ingredient = self.repository.create(ingredient)

        # 添加别名
        if data.aliases:
            for alias_name in data.aliases:
                if not self.repository.check_alias_exists(alias_name):
                    alias = IngredientAlias(
                        id=str(uuid.uuid4()),
                        ingredient_id=ingredient.id,
                        alias=alias_name
                    )
                    self.repository.add_alias(alias)

        return self._to_response(ingredient)

    def update_ingredient(self, ingredient_id: str, data: IngredientUpdate) -> Optional[IngredientResponse]:
        """更新食材"""
        ingredient = self.repository.get_by_id(ingredient_id)
        if not ingredient:
            return None

        # 更新字段
        update_data = data.model_dump(exclude_unset=True)

        # 处理列表类型字段的JSON序列化
        if "season_months" in update_data and update_data["season_months"] is not None:
            update_data["season_months"] = json.dumps(update_data["season_months"])
        if "allergens" in update_data and update_data["allergens"] is not None:
            update_data["allergens"] = json.dumps(update_data["allergens"])

        # 名称变更时重算拼音
        if "canonical_name" in update_data and update_data["canonical_name"]:
            update_data["pinyin"] = to_pinyin(update_data["canonical_name"])

        for key, value in update_data.items():
            setattr(ingredient, key, value)

        ingredient.updated_at = datetime.utcnow()
        ingredient = self.repository.update(ingredient)

        return self._to_response(ingredient)

    def delete_ingredient(self, ingredient_id: str) -> bool:
        """删除食材（软删除，进入回收站），若仍被菜谱使用则拒绝删除"""
        if not self.repository.get_by_id(ingredient_id):
            return False
        recipes = self.repository.find_recipes_by_ingredient(ingredient_id)
        if recipes:
            titles = "、".join(title for _, title in recipes)
            raise ValueError(
                f"该食材已被 {len(recipes)} 个菜谱使用（{titles}），请先修改或删除这些菜谱后再试"
            )
        return self.repository.soft_delete(ingredient_id)

    def list_deleted(self, page: int = 1, page_size: int = 20) -> IngredientListResponse:
        """列出回收站中的食材（已软删除）"""
        ingredients, total = self.repository.list_deleted(page=page, page_size=page_size)
        return IngredientListResponse(
            data=[self._to_response(i) for i in ingredients],
            total=total, page=page, page_size=page_size
        )

    def restore_ingredient(self, ingredient_id: str) -> Optional[IngredientResponse]:
        """恢复回收站中的食材"""
        try:
            ingredient = self.repository.restore(ingredient_id)
        except IntegrityError as e:
            self.repository.db.rollback()
            raise ValueError("同名食材已存在，无法恢复") from e
        if not ingredient:
            return None
        return self._to_response(ingredient)

    def hard_delete_ingredient(self, ingredient_id: str) -> bool:
        """彻底删除回收站中的食材，仍被菜谱或库存引用时拒绝"""
        if not self.repository.get_by_id_any(ingredient_id):
            return False
        recipes = self.repository.find_recipes_by_ingredient_any(ingredient_id)
        if recipes:
            titles = "、".join(title for _, title in recipes)
            raise ValueError(
                f"该食材仍被 {len(recipes)} 个菜谱引用（{titles}），无法彻底删除"
            )
        inventory = self.repository.find_inventory_by_ingredient(ingredient_id)
        if inventory:
            raise ValueError(
                f"该食材仍被 {len(inventory)} 条库存记录引用，无法彻底删除"
            )
        return self.repository.hard_delete(ingredient_id)

    def add_alias(self, ingredient_id: str, alias_name: str) -> Optional[IngredientAlias]:
        """添加别名"""
        ingredient = self.repository.get_by_id(ingredient_id)
        if not ingredient:
            return None

        # 检查别名是否已存在
        if self.repository.check_alias_exists(alias_name):
            raise ValueError(f"别名 '{alias_name}' 已存在")

        alias = IngredientAlias(
            id=str(uuid.uuid4()),
            ingredient_id=ingredient_id,
            alias=alias_name
        )
        return self.repository.add_alias(alias)

    def remove_alias(self, alias_id: str) -> bool:
        """删除别名"""
        return self.repository.remove_alias(alias_id)

    def _to_response(self, ingredient: Ingredient) -> IngredientResponse:
        """将数据库模型转换为响应模式"""
        # 解析JSON字段
        season_months = None
        if ingredient.season_months:
            try:
                season_months = json.loads(ingredient.season_months)
            except json.JSONDecodeError:
                season_months = []

        allergens = None
        if ingredient.allergens:
            try:
                allergens = json.loads(ingredient.allergens)
            except json.JSONDecodeError:
                allergens = []

        # 获取别名
        aliases = self.repository.get_aliases(ingredient.id)

        return IngredientResponse(
            id=ingredient.id,
            canonical_name=ingredient.canonical_name,
            pinyin=ingredient.pinyin,
            category_id=ingredient.category_id,
            category_name=self._category_name(ingredient.category_id),
            season_months=season_months,
            allergens=allergens,
            nutrition_ref=ingredient.nutrition_ref,
            confidence_status=ingredient.confidence_status,
            aliases=[
                {"id": a.id, "alias": a.alias, "created_at": a.created_at}
                for a in aliases
            ],
            deleted_at=ingredient.deleted_at,
            created_at=ingredient.created_at,
            updated_at=ingredient.updated_at
        )

    def _category_name(self, category_id: Optional[str]) -> Optional[str]:
        """查询食材分类名称"""
        return self.repository.get_category_name(category_id)
