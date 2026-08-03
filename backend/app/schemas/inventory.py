"""库存相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class InventoryItemBase(BaseModel):
    """库存物品基础模式"""
    household_id: str = Field(..., description="家庭ID")
    ingredient_id: str = Field(..., description="食材ID")
    quantity: Optional[str] = Field(None, description="数量")
    unit: Optional[str] = Field(None, description="单位")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    note: Optional[str] = Field(None, description="备注")


class InventoryItemCreate(InventoryItemBase):
    """创建库存物品"""
    pass


class InventoryItemUpdate(BaseModel):
    """更新库存物品"""
    quantity: Optional[str] = Field(None, description="数量")
    unit: Optional[str] = Field(None, description="单位")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    note: Optional[str] = Field(None, description="备注")
    is_expired: Optional[bool] = Field(None, description="是否过期")


class InventoryItemResponse(BaseModel):
    """库存物品响应"""
    id: str
    household_id: str
    ingredient_id: str
    ingredient_name: str
    quantity: Optional[str]
    unit: Optional[str]
    expires_at: Optional[datetime]
    note: Optional[str]
    is_expired: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    """库存列表响应"""
    data: List[InventoryItemResponse]
    total: int
    page: int
    page_size: int


class InventorySearchRequest(BaseModel):
    """库存搜索请求"""
    household_id: str = Field(..., description="家庭ID")
    ingredient_id: Optional[str] = Field(None, description="食材ID筛选")
    include_expired: bool = Field(False, description="是否包含过期物品")
    expires_within_days: Optional[int] = Field(None, description="即将过期天数")


class HouseholdCreate(BaseModel):
    """创建家庭"""
    name: str = Field(..., min_length=1, max_length=100, description="家庭名称")
    description: Optional[str] = Field(None, description="描述")


class HouseholdResponse(BaseModel):
    """家庭响应"""
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HouseholdListResponse(BaseModel):
    """家庭列表响应"""
    data: List[HouseholdResponse]
    total: int
    page: int
    page_size: int
