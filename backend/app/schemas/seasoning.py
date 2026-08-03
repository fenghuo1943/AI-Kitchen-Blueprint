"""调料相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class SeasoningBase(BaseModel):
    """调料基础模式"""
    canonical_name: str = Field(..., min_length=1, max_length=100, description="标准名称")
    category_id: Optional[str] = Field(None, description="调料分类ID")


class SeasoningCreate(SeasoningBase):
    """创建调料"""
    pass


class SeasoningUpdate(BaseModel):
    """更新调料"""
    canonical_name: Optional[str] = Field(None, min_length=1, max_length=100)
    category_id: Optional[str] = None


class SeasoningResponse(BaseModel):
    """调料响应"""
    id: str
    canonical_name: str
    pinyin: Optional[str]
    category_id: Optional[str]
    category_name: Optional[str]
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


class SeasoningListResponse(BaseModel):
    """调料列表响应"""
    data: List[SeasoningResponse]
    total: int
    page: int
    page_size: int


class SeasoningSearchRequest(BaseModel):
    """调料搜索请求"""
    query: Optional[str] = Field(None, description="搜索关键词")
    category_id: Optional[str] = Field(None, description="分类筛选")
