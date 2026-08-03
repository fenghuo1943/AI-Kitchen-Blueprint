"""食材业务逻辑层"""
import json
import uuid
from typing import Optional, List
from datetime import datetime

from app.core.pinyin import to_pinyin
from app.db.models import Ingredient, IngredientAlias
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
            category=request.category,
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

        # 创建食材
        ingredient = Ingredient(
            id=str(uuid.uuid4()),
            canonical_name=data.canonical_name,
            pinyin=to_pinyin(data.canonical_name),
            category=data.category,
            category_id=data.category_id,
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
        """删除食材（软删除）"""
        return self.repository.soft_delete(ingredient_id)

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
            category=ingredient.category,
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
            created_at=ingredient.created_at,
            updated_at=ingredient.updated_at
        )

    def _category_name(self, category_id: Optional[str]) -> Optional[str]:
        """查询食材分类名称"""
        return self.repository.get_category_name(category_id)
