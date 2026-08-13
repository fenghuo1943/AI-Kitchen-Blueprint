"""AI 采集入库相关的数据模式"""
from typing import Dict, List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.ingestion import IngestionResponse
from app.schemas.recipe import RecipeResponse


class AICollectionCreate(BaseModel):
    """提交 AI 采集任务"""
    request_text: str = Field("", description="菜名/主题/逗号分隔食材/补全请求；手动模式可为空")
    mode: Literal["topic", "ingredients", "complete", "manual"] = Field("topic", description="采集模式")
    target_recipe_id: Optional[str] = Field(None, description="补全模式的目标菜谱 ID")
    max_results: int = Field(15, ge=1, le=20, description="最多采集页数")
    llm_provider: Optional[str] = Field(None, description="采集用 LLM 供应商：ollama/anthropic/deepseek/openrouter/openai_compat（缺省取配置）")
    llm_model: Optional[str] = Field(None, description="采集用模型名（缺省取配置）")
    search_sites: Optional[List[str]] = Field(None, description="限定搜索的站点域名列表，如 ['xiachufang.com']；缺省取全局配置 AI_COLLECT_SEARCH_SITES")
    manual_url: Optional[str] = Field(None, description="手动模式：来源页面 URL（登录墙/反爬站点如小红书）；粘贴结构化菜谱 JSON 时可为空")
    manual_content: Optional[str] = Field(None, description="手动模式：用户粘贴的页面正文，或 AI 生成的结构化菜谱 JSON")


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
    source_url: Optional[str] = None       # 主来源（第一个）
    source_urls: List[str] = []           # 参考的全部来源 URL
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
    search_sites: Optional[List[str]] = None
    manual_url: Optional[str] = None
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
    default_search_sites: List[str] = Field(default_factory=list, description="全局默认限定搜索的域名列表")


class BrowserStatusResponse(BaseModel):
    """浏览器抓取（Playwright）配置状态（前端手动模式提示用）"""
    enabled: bool = Field(..., description="总开关 BROWSER_FETCH_ENABLED 是否开启")
    available: bool = Field(..., description="当前环境是否可用（开关 + playwright 已装 + 有浏览器）")
    reason: str = Field("", description="不可用原因")
    profile_exists: bool = Field(False, description="登录态 profile 目录是否已存在（是否登录过）")


class BrowserLoginRequest(BaseModel):
    """浏览器登录请求"""
    url: str = Field("https://www.xiaohongshu.com", description="要登录的站点 URL，默认小红书首页")


class BrowserLoginResponse(BaseModel):
    """浏览器登录响应"""
    ok: bool
    message: str = ""


class BrowserFetchRequest(BaseModel):
    """浏览器抓取请求"""
    url: str = Field(..., description="要抓取的页面 URL（支持小红书 xhslink.com 短链）")


class BrowserFetchResponse(BaseModel):
    """浏览器抓取响应"""
    url: str
    content: str = Field("", description="清洗后的页面正文")
    error: Optional[str] = None
