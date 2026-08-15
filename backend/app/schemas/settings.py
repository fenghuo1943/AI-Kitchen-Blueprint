"""用户/家庭设置相关的数据模式"""
from typing import Optional
from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """设置响应（未设置项返回默认值）"""
    page_size_desktop: int = Field(30, ge=5, le=100, description="电脑端每页数量")
    page_size_mobile: int = Field(20, ge=5, le=100, description="手机端每页数量")


class SettingsUpdate(BaseModel):
    """设置更新请求（部分更新，只提交要改的项）"""
    page_size_desktop: Optional[int] = Field(None, ge=5, le=100, description="电脑端每页数量")
    page_size_mobile: Optional[int] = Field(None, ge=5, le=100, description="手机端每页数量")
