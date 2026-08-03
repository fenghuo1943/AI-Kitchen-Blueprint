"""推荐相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class RecommendationRequest(BaseModel):
    """推荐请求"""
    ingredients: List[str] = Field(default_factory=list, description="现有食材列表（名称或ID）")
    season_month: Optional[str] = Field(None, description="当前月份 [1-12]")
    max_minutes: Optional[int] = Field(None, description="最大烹饪时间（分钟）")
    people_count: Optional[int] = Field(None, description="人数")
    equipment: Optional[List[str]] = Field(None, description="设备标签（如快炒、炖煮、烤箱）")
    diet_restrictions: Optional[List[str]] = Field(None, description="忌口或过敏原限制（如 gluten、dairy）")
    goals: Optional[List[str]] = Field(None, description="目标标签（如快速、控脂）")
    allow_missing: bool = Field(True, description="是否允许缺料")


class RecommendationReason(BaseModel):
    """推荐理由"""
    recipe_id: str = Field(..., description="菜谱ID")
    matched_ingredients: List[str] = Field(default_factory=list, description="已匹配的食材")
    missing_ingredients: List[str] = Field(default_factory=list, description="缺少的食材")
    coverage_score: float = Field(..., description="食材覆盖率 (0-1)")
    match_score: float = Field(..., description="匹配分数 (0-1)")
    time_score: float = Field(..., description="时间分数 (0-1)")
    tag_score: float = Field(..., description="标签匹配分数 (0-1)")
    overall_score: float = Field(..., description="综合分数 (0-1)")
    explanation: str = Field(..., description="推荐解释")


class RecommendationResult(BaseModel):
    """推荐结果"""
    recipe_id: str = Field(..., description="菜谱ID")
    recipe_title: str = Field(..., description="菜谱名称")
    recipe_summary: Optional[str] = Field(None, description="菜谱简介")
    servings: Optional[int] = Field(None, description="份量")
    total_minutes: Optional[int] = Field(None, description="总时间（分钟）")
    difficulty: Optional[str] = Field(None, description="难度")
    matched_ingredients: List[str] = Field(default_factory=list, description="已匹配的食材")
    missing_ingredients: List[str] = Field(default_factory=list, description="缺少的食材")
    coverage_score: float = Field(..., description="食材覆盖率 (0-1)")
    overall_score: float = Field(..., description="综合分数 (0-1)")
    reason: str = Field(..., description="推荐理由")


class RecommendationResponse(BaseModel):
    """推荐响应"""
    results: List[RecommendationResult] = Field(default_factory=list, description="推荐结果列表")
    total: int = Field(..., description="总数")
    filters_applied: dict = Field(default_factory=dict, description="已应用的筛选条件")
    fallback_reason: Optional[str] = Field(None, description="降级原因（无结果时）")


class IngredientCoverageRequest(BaseModel):
    """食材覆盖率计算请求"""
    recipe_id: str = Field(..., description="菜谱ID")
    available_ingredients: List[str] = Field(..., description="现有食材列表")


class IngredientCoverageResponse(BaseModel):
    """食材覆盖率计算响应"""
    recipe_id: str
    recipe_title: str
    coverage_score: float = Field(..., description="覆盖率 (0-1)")
    matched_ingredients: List[str] = Field(default_factory=list, description="已匹配的食材")
    missing_ingredients: List[str] = Field(default_factory=list, description="缺少的食材")
    required_ingredients: List[str] = Field(default_factory=list, description="必需的食材")
