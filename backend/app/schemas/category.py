"""分类相关的数据模式（菜谱/食材/调料分类共用）"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class CategoryBase(BaseModel):
    """分类基础模式"""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    parent_id: Optional[str] = Field(None, description="父分类ID（仅菜谱分类支持层级）")
    sort_order: int = Field(0, description="排序")


class CategoryCreate(BaseModel):
    """创建分类"""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    parent_id: Optional[str] = Field(None, description="父分类ID（仅菜谱分类支持层级）")


class CategoryUpdate(BaseModel):
    """更新分类"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    """分类响应"""
    id: str
    name: str
    parent_id: Optional[str]
    sort_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _normalize_datetime(cls, v):
        """兼容数据库零值日期（如 '0000-00-00 00:00:00'）或空值，避免序列化报错"""
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            if not s or s.startswith("0000-00-00"):
                return None
        return v

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """分类列表响应"""
    data: List[CategoryResponse]
    total: int
