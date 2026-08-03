"""菜谱相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class RecipeIngredientBase(BaseModel):
    """菜谱食材基础模式"""
    ingredient_id: str = Field(..., description="食材ID")
    quantity: Optional[str] = Field(None, description="数量")
    unit: Optional[str] = Field(None, description="单位")
    raw_quantity: Optional[str] = Field(None, description="原始数量文本")
    preparation: Optional[str] = Field(None, description="预处理方式")
    optional: bool = Field(False, description="是否可选")
    sort_order: int = Field(0, description="排序")


class RecipeStepBase(BaseModel):
    """菜谱步骤基础模式"""
    step_no: int = Field(..., description="步骤序号")
    instruction: str = Field(..., description="操作说明")
    duration_minutes: Optional[int] = Field(None, description="预计时长（分钟）")
    image_url: Optional[str] = Field(None, description="图片URL")


class RecipeBase(BaseModel):
    """菜谱基础模式"""
    title: str = Field(..., min_length=1, max_length=200, description="菜谱名称")
    summary: Optional[str] = Field(None, description="简述")
    servings: Optional[int] = Field(None, ge=1, description="份量")
    prep_minutes: Optional[int] = Field(None, ge=0, description="准备时间（分钟）")
    cook_minutes: Optional[int] = Field(None, ge=0, description="烹饪时间（分钟）")
    difficulty: Optional[str] = Field(None, description="难度")
    source_id: Optional[str] = Field(None, description="来源ID")


class RecipeCreate(RecipeBase):
    """创建菜谱"""
    ingredients: List[RecipeIngredientBase] = Field(default_factory=list, description="食材列表")
    steps: List[RecipeStepBase] = Field(default_factory=list, description="步骤列表")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class RecipeUpdate(BaseModel):
    """更新菜谱"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    summary: Optional[str] = None
    servings: Optional[int] = Field(None, ge=1)
    prep_minutes: Optional[int] = Field(None, ge=0)
    cook_minutes: Optional[int] = Field(None, ge=0)
    difficulty: Optional[str] = None
    status: Optional[str] = None


class RecipeIngredientResponse(BaseModel):
    """菜谱食材响应"""
    id: str
    ingredient_id: str
    ingredient_name: str
    quantity: Optional[str]
    unit: Optional[str]
    preparation: Optional[str]
    optional: bool
    sort_order: int

    class Config:
        from_attributes = True


class RecipeStepResponse(BaseModel):
    """菜谱步骤响应"""
    id: str
    step_no: int
    instruction: str
    duration_minutes: Optional[int]
    image_url: Optional[str]

    class Config:
        from_attributes = True


class RecipeTagResponse(BaseModel):
    """菜谱标签响应"""
    id: str
    name: str
    type: str

    class Config:
        from_attributes = True


class RecipeResponse(RecipeBase):
    """菜谱响应"""
    id: str
    status: str
    revision: int
    created_by: Optional[str]
    ingredients: List[RecipeIngredientResponse] = []
    steps: List[RecipeStepResponse] = []
    tags: List[RecipeTagResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecipeListResponse(BaseModel):
    """菜谱列表响应"""
    data: List[RecipeResponse]
    total: int
    page: int
    page_size: int


class RecipeSearchRequest(BaseModel):
    """菜谱搜索请求"""
    query: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[str] = Field(None, description="状态筛选")
    difficulty: Optional[str] = Field(None, description="难度筛选")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    max_cook_time: Optional[int] = Field(None, description="最大烹饪时间")
