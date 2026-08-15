"""食材相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class IngredientBase(BaseModel):
    """食材基础模式"""
    canonical_name: str = Field(..., min_length=1, max_length=100, description="标准名称")
    category_id: Optional[str] = Field(None, description="食材分类ID")
    season_months: Optional[List[str]] = Field(None, description="应季月份 [1-12]")
    allergens: Optional[List[str]] = Field(None, description="过敏原")
    nutrition_ref: Optional[str] = Field(None, description="营养参考")
    confidence_status: str = Field("verified", description="置信度状态")


class IngredientCreate(IngredientBase):
    """创建食材"""
    aliases: Optional[List[str]] = Field(None, description="别名列表")


class IngredientUpdate(BaseModel):
    """更新食材"""
    canonical_name: Optional[str] = Field(None, min_length=1, max_length=100)
    category_id: Optional[str] = None
    season_months: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    nutrition_ref: Optional[str] = None
    confidence_status: Optional[str] = None


class IngredientAliasResponse(BaseModel):
    """食材别名响应"""
    id: str
    alias: str
    created_at: datetime

    class Config:
        from_attributes = True


class IngredientResponse(IngredientBase):
    """食材响应"""
    id: str
    pinyin: Optional[str]
    category_name: Optional[str]
    aliases: List[IngredientAliasResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IngredientListResponse(BaseModel):
    """食材列表响应"""
    data: List[IngredientResponse]
    total: int
    page: int
    page_size: int


class IngredientSearchRequest(BaseModel):
    """食材搜索请求"""
    query: Optional[str] = Field(None, description="搜索关键词")
    category_id: Optional[str] = Field(None, description="食材分类ID筛选")
    allergens_exclude: Optional[List[str]] = Field(None, description="排除的过敏原")
    season_month: Optional[str] = Field(None, description="应季月份筛选")
