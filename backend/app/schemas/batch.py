"""批量操作相关的数据模式（菜谱/食材/调料回收站批量删除共用）"""
from typing import List
from pydantic import BaseModel, Field


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[str] = Field(..., min_length=1, max_length=1000, description="要删除的ID列表")


class BatchDeleteFailure(BaseModel):
    """批量删除失败项"""
    id: str
    name: str
    reason: str


class BatchDeleteResponse(BaseModel):
    """批量删除响应（尽力而为：删除可删的，返回被引用等无法删除的失败项）"""
    deleted_count: int = Field(..., description="成功删除的数量")
    failed: List[BatchDeleteFailure] = Field(default_factory=list, description="无法删除的项")
