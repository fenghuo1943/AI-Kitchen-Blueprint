"""浏览历史相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class HistoryCreate(BaseModel):
    """手动记录历史请求"""
    recipe_id: str = Field(..., description="菜谱ID")


class HistoryResponse(BaseModel):
    """浏览历史响应"""
    id: str
    recipe_id: str
    recipe_title: str
    cover: Optional[str]
    viewed_at: datetime

    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    """浏览历史列表响应"""
    data: List[HistoryResponse]
    total: int
    page: int
    page_size: int
