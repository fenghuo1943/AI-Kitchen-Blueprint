"""库存业务逻辑层"""
import uuid
from typing import Optional, List
from datetime import datetime

from app.db.models import InventoryItem, Household
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.services.household_resolver import resolve_default_household_id
from app.schemas.inventory import (
    InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse,
    InventoryListResponse, InventorySearchRequest, HouseholdCreate, HouseholdResponse,
    HouseholdListResponse
)


class InventoryService:
    """库存服务类"""

    def __init__(
        self,
        inventory_repository: InventoryRepository,
        ingredient_repository: IngredientRepository
    ):
        self.inventory_repository = inventory_repository
        self.ingredient_repository = ingredient_repository

    def get_item(self, item_id: str) -> Optional[InventoryItemResponse]:
        """获取库存物品详情"""
        item = self.inventory_repository.get_by_id(item_id)
        if not item:
            return None
        return self._to_response(item)

    def search_items(self, request: InventorySearchRequest, page: int = 1, page_size: int = 20) -> InventoryListResponse:
        """搜索库存物品"""
        items, total = self.inventory_repository.search(
            household_id=request.household_id,
            ingredient_id=request.ingredient_id,
            include_expired=request.include_expired,
            expires_within_days=request.expires_within_days,
            page=page,
            page_size=page_size
        )
        return InventoryListResponse(
            data=[self._to_response(i) for i in items],
            total=total,
            page=page,
            page_size=page_size
        )

    def create_item(self, data: InventoryItemCreate) -> InventoryItemResponse:
        """创建库存物品"""
        # 家庭未显式指定时落到默认家庭
        household_id = data.household_id or resolve_default_household_id(self.inventory_repository.db)
        # 验证家庭是否存在（显式传入的 id 仍校验；默认路径必然存在）
        household = self.inventory_repository.get_household(household_id)
        if not household:
            raise ValueError("家庭不存在")

        # 验证食材是否存在
        ingredient = self.ingredient_repository.get_by_id(data.ingredient_id)
        if not ingredient:
            raise ValueError("食材不存在")

        # 检查是否已存在相同食材的库存
        existing_items, _ = self.inventory_repository.search(
            household_id=household_id,
            ingredient_id=data.ingredient_id,
            include_expired=True
        )
        if existing_items:
            raise ValueError("该食材已存在库存记录，请更新现有记录")

        # 创建库存物品
        item = InventoryItem(
            id=str(uuid.uuid4()),
            household_id=household_id,
            ingredient_id=data.ingredient_id,
            quantity=data.quantity,
            unit=data.unit,
            expires_at=data.expires_at,
            note=data.note,
            is_expired=0
        )
        item = self.inventory_repository.create(item)

        return self._to_response(item)

    def update_item(self, item_id: str, data: InventoryItemUpdate) -> Optional[InventoryItemResponse]:
        """更新库存物品"""
        item = self.inventory_repository.get_by_id(item_id)
        if not item:
            return None

        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "is_expired":
                setattr(item, key, 1 if value else 0)
            else:
                setattr(item, key, value)

        item.updated_at = datetime.utcnow()
        item = self.inventory_repository.update(item)

        return self._to_response(item)

    def delete_item(self, item_id: str) -> bool:
        """删除库存物品（软删除）"""
        return self.inventory_repository.soft_delete(item_id)

    def check_expiry(self, item_id: str) -> Optional[InventoryItemResponse]:
        """检查物品是否过期"""
        item = self.inventory_repository.check_expiry(item_id)
        if not item:
            return None
        return self._to_response(item)

    def get_expiring_soon(self, household_id: str, days: int = 7) -> List[InventoryItemResponse]:
        """获取即将过期的物品"""
        items = self.inventory_repository.get_expiring_soon(household_id, days)
        return [self._to_response(i) for i in items]

    def create_household(self, data: HouseholdCreate) -> HouseholdResponse:
        """创建家庭"""
        household = Household(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description
        )
        household = self.inventory_repository.create_household(household)
        return HouseholdResponse(
            id=household.id,
            name=household.name,
            description=household.description,
            created_at=household.created_at,
            updated_at=household.updated_at
        )

    def list_households(self, page: int = 1, page_size: int = 20) -> HouseholdListResponse:
        """获取家庭列表"""
        households, total = self.inventory_repository.list_households(page, page_size)
        return HouseholdListResponse(
            data=[
                HouseholdResponse(
                    id=h.id,
                    name=h.name,
                    description=h.description,
                    created_at=h.created_at,
                    updated_at=h.updated_at
                )
                for h in households
            ],
            total=total,
            page=page,
            page_size=page_size
        )

    def get_household(self, household_id: str) -> Optional[HouseholdResponse]:
        """获取家庭信息"""
        household = self.inventory_repository.get_household(household_id)
        if not household:
            return None
        return HouseholdResponse(
            id=household.id,
            name=household.name,
            description=household.description,
            created_at=household.created_at,
            updated_at=household.updated_at
        )

    def _to_response(self, item: InventoryItem) -> InventoryItemResponse:
        """将数据库模型转换为响应模式"""
        # 获取食材名称
        ingredient = self.ingredient_repository.get_by_id(item.ingredient_id)
        ingredient_name = ingredient.canonical_name if ingredient else "未知"

        return InventoryItemResponse(
            id=item.id,
            household_id=item.household_id,
            ingredient_id=item.ingredient_id,
            ingredient_name=ingredient_name,
            quantity=item.quantity,
            unit=item.unit,
            expires_at=item.expires_at,
            note=item.note,
            is_expired=bool(item.is_expired),
            created_at=item.created_at,
            updated_at=item.updated_at
        )
