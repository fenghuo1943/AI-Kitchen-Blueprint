"""RAG 语义检索 / 索引管理接口模型"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="自然语言查询")
    max_cook_time: Optional[int] = Field(None, ge=0, description="最大总时长（分钟）硬约束")
    tags: Optional[List[str]] = Field(None, description="标签硬约束")
    ingredient_ids: Optional[List[str]] = Field(None, description="食材 ID 硬约束")
    category_id: Optional[str] = Field(None, description="分类硬约束")
    household_id: Optional[str] = Field(None, description="家庭 ID（用于偏好加权）")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="返回条数（默认 10）")


class RagChunk(BaseModel):
    chunk_type: str
    text: str
    vector_score: float


class RagSearchItem(BaseModel):
    recipe_id: str
    title: str
    cover: Optional[str] = None
    summary: Optional[str] = None
    score: float = 0.0
    matched_ingredients: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    chunks: List[RagChunk] = Field(default_factory=list)  # 命中块原文，供后续 LLM 问答消费


class RagSearchResponse(BaseModel):
    results: List[RagSearchItem] = Field(default_factory=list)
    total: int = 0
    engine_available: bool = True
    took_ms: int = 0
    error: Optional[str] = Field(None, description="引擎不可用时的可读原因")


class IndexStatusResponse(BaseModel):
    indexed_count: int  # 已入向量库的去重菜谱数
    published_count: int  # 当前已发布且未删除的菜谱数
    last_rebuild_at: Optional[datetime] = None
    running: List[str] = Field(default_factory=list)
    queued: List[str] = Field(default_factory=list)
    failed: int = 0
    last_error: Dict[str, str] = Field(default_factory=dict)
    breakdown_by_type: Dict[str, int] = Field(default_factory=dict)
