"""库存管理 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.services.inventory_service import InventoryService
from app.schemas.inventory import (
    InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse,
    InventoryListResponse, InventorySearchRequest, HouseholdCreate, HouseholdResponse
)

router = APIRouter(prefix="/inventory", tags=["库存管理"])


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryService:
    """获取库存服务实例"""
    inventory_repo = InventoryRepository(db)
    ingredient_repo = IngredientRepository(db)
    return InventoryService(inventory_repo, ingredient_repo)


# 家庭管理接口
@router.post("/households", response_model=HouseholdResponse, status_code=201)
def create_household(
    data: HouseholdCreate,
    service: InventoryService = Depends(get_inventory_service)
):
    """创建家庭"""
    return service.create_household(data)


@router.get("/households/{household_id}", response_model=HouseholdResponse)
def get_household(
    household_id: str,
    service: InventoryService = Depends(get_inventory_service)
):
    """获取家庭信息"""
    result = service.get_household(household_id)
    if not result:
        raise HTTPException(status_code=404, detail="家庭不存在")
    return result


# 库存物品管理接口
@router.get("/items", response_model=InventoryListResponse)
def list_inventory_items(
    household_id: str = Query(..., description="家庭ID"),
    ingredient_id: Optional[str] = Query(None, description="食材ID筛选"),
    include_expired: bool = Query(False, description="是否包含过期物品"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: InventoryService = Depends(get_inventory_service)
):
    """获取库存物品列表"""
    request = InventorySearchRequest(
        household_id=household_id,
        ingredient_id=ingredient_id,
        include_expired=include_expired
    )
    return service.search_items(request, page=page, page_size=page_size)


@router.get("/items/{item_id}", response_model=InventoryItemResponse)
def get_inventory_item(
    item_id: str,
    service: InventoryService = Depends(get_inventory_service)
):
    """获取库存物品详情"""
    result = service.get_item(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="库存物品不存在")
    return result


@router.post("/items", response_model=InventoryItemResponse, status_code=201)
def create_inventory_item(
    data: InventoryItemCreate,
    service: InventoryService = Depends(get_inventory_service)
):
    """创建库存物品"""
    try:
        return service.create_item(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/items/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(
    item_id: str,
    data: InventoryItemUpdate,
    service: InventoryService = Depends(get_inventory_service)
):
    """更新库存物品"""
    result = service.update_item(item_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="库存物品不存在")
    return result


@router.delete("/items/{item_id}", status_code=204)
def delete_inventory_item(
    item_id: str,
    service: InventoryService = Depends(get_inventory_service)
):
    """删除库存物品"""
    if not service.delete_item(item_id):
        raise HTTPException(status_code=404, detail="库存物品不存在")
    return None


@router.get("/expiring-soon", response_model=list[InventoryItemResponse])
def get_expiring_soon(
    household_id: str = Query(..., description="家庭ID"),
    days: int = Query(7, ge=1, le=30, description="天数范围"),
    service: InventoryService = Depends(get_inventory_service)
):
    """获取即将过期的物品"""
    return service.get_expiring_soon(household_id, days)
