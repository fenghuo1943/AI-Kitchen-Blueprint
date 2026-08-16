"""入库任务相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class IngestionRecipeData(BaseModel):
    """入库菜谱数据（人工录入）"""
    title: str = Field(..., min_length=1, description="菜谱名称")
    summary: Optional[str] = Field(None, description="简述")
    servings: Optional[int] = Field(None, description="份量")
    prep_minutes: Optional[int] = Field(None, description="准备时间")
    cook_minutes: Optional[int] = Field(None, description="烹饪时间")
    difficulty: Optional[str] = Field(None, description="难度")
    category: Optional[str] = Field(None, description="菜谱分类（须在规范分类清单内，否则按标题自动分类）")
    ingredients: List[dict] = Field(default_factory=list, description="食材列表")
    steps: List[dict] = Field(default_factory=list, description="步骤列表")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class IngestionCreate(BaseModel):
    """创建入库任务"""
    source_type: str = Field(..., description="来源类型: file, url, manual")
    source_ref: Optional[str] = Field(None, description="文件路径或URL")
    recipe_data: Optional[IngestionRecipeData] = Field(None, description="人工录入的菜谱数据")
    import_mode: str = Field("draft", description="导入模式: draft, review")
    metadata: Optional[dict] = Field(None, description="来源元数据")


class IngestionResponse(BaseModel):
    """入库任务响应"""
    id: str
    source_id: Optional[str]
    status: str
    stage: str
    error_code: Optional[str]
    result_recipe_id: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IngestionListResponse(BaseModel):
    """入库任务列表响应"""
    data: List[IngestionResponse]
    total: int
    page: int
    page_size: int


class IngestionStageLog(BaseModel):
    """入库阶段日志"""
    stage: str
    status: str
    message: Optional[str]
    timestamp: datetime


class IngestionDetailResponse(IngestionResponse):
    """入库任务详情响应"""
    source_type: Optional[str]
    source_url: Optional[str]
    raw_hash: Optional[str]
    logs: List[IngestionStageLog] = []
