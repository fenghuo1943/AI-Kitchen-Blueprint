"""AI 采集入库相关的数据模式"""
from typing import Dict, List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.ingestion import IngestionResponse
from app.schemas.recipe import RecipeResponse


class AICollectionCreate(BaseModel):
    """提交 AI 采集任务"""
    request_text: str = Field(..., min_length=1, description="菜名/主题/逗号分隔食材/补全请求")
    mode: Literal["topic", "ingredients", "complete"] = Field("topic", description="采集模式")
    target_recipe_id: Optional[str] = Field(None, description="补全模式的目标菜谱 ID")
    max_results: int = Field(5, ge=1, le=10, description="最多采集页数")
    llm_provider: Optional[str] = Field(None, description="采集用 LLM 供应商：ollama/anthropic（缺省取配置）")
    llm_model: Optional[str] = Field(None, description="采集用模型名（缺省取配置）")


class LLMModelOption(BaseModel):
    """可用的 LLM 模型选项"""
    provider: str
    model: str
    label: str


class LLMModelsResponse(BaseModel):
    """可用模型列表 + 默认选择"""
    models: List[LLMModelOption] = []
    default_provider: str
    default_model: str


class CandidateResponse(BaseModel):
    """采集候选（待审菜谱）"""
    id: str
    job_id: str
    recipe: Optional[RecipeResponse] = None
    action: str
    merge_mode: str
    source_url: Optional[str] = None
    normalized_title: Optional[str] = None
    core_ingredients: List[str] = []
    match_scores: Dict = {}
    reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class AICollectionJobResponse(IngestionResponse):
    """AI 采集任务详情"""
    request_text: Optional[str] = None
    collection_mode: str = "topic"
    target_recipe_id: Optional[str] = None
    candidates_count: int = 0
    reason: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    candidates: List[CandidateResponse] = []


class PaginatedCandidateResponse(BaseModel):
    """候选分页响应"""
    data: List[CandidateResponse]
    total: int
    page: int
    page_size: int


class ConfigStatusResponse(BaseModel):
    """AI 采集配置状态（前端横幅用）"""
    tavily_configured: bool
    llm_provider: str
    llm_configured: bool
    llm_model: Optional[str] = None
    llm_health: Dict = {}
