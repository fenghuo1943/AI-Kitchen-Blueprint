"""每日菜单相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class MealPlanCreate(BaseModel):
    """添加菜谱到某天"""
    recipe_id: str = Field(..., description="菜谱ID")
    date: str = Field(..., description="日期 YYYY-MM-DD")


class MealPlanItem(BaseModel):
    """菜单项"""
    recipe_id: str
    title: str
    cover: Optional[str]
    cook_time: Optional[int]
    added_at: Optional[datetime]


class MenuNameItem(BaseModel):
    """菜单聚合的食材/调料项"""
    id: str
    name: str


class MenuByDateResponse(BaseModel):
    """某天菜单"""
    date: str
    list: List[MealPlanItem]
    ing_list: List[MenuNameItem]
    sea_list: List[MenuNameItem]


class MonthDatesResponse(BaseModel):
    """某月有菜单的日期"""
    dates: List[str]


class WaterfallGroup(BaseModel):
    """瀑布流按天分组"""
    date: str
    recipes: List[MealPlanItem]


class WaterfallResponse(BaseModel):
    """菜单瀑布流"""
    list: List[WaterfallGroup]
    total_page: int
    page: int
    page_size: int
