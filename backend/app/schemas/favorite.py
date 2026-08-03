"""收藏相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class FavoriteCreate(BaseModel):
    """收藏请求"""
    recipe_id: str = Field(..., description="菜谱ID")


class FavoriteResponse(BaseModel):
    """收藏响应"""
    id: str
    recipe_id: str
    recipe_title: str
    cover: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    """收藏列表响应"""
    data: List[FavoriteResponse]
    total: int
    page: int
    page_size: int
