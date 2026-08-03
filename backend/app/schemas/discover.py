"""发现/推荐相关的数据模式"""
from typing import Optional, List
from pydantic import BaseModel


class DiscoverRecipe(BaseModel):
    """推荐菜谱项"""
    id: str
    title: str
    cover: Optional[str]
    summary: Optional[str]
    cook_time: Optional[int]
    is_favorited: bool = False
    is_in_today_menu: bool = False
    cooked_count: int = 0


class DiscoverResponse(BaseModel):
    """推荐结果"""
    list: List[DiscoverRecipe]
