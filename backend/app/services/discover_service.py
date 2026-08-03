"""发现/推荐业务逻辑层（参考 cook DiscoverService）"""
import hashlib
import random
from datetime import date
from typing import List

from app.repositories.discover_repository import DiscoverRepository
from app.schemas.discover import DiscoverRecipe, DiscoverResponse


def _daily_rand(recipe_id: str) -> float:
    """按日期固定的随机值：当日稳定、每日变化（等价 cook 的 RAND(CURDATE())）"""
    h = hashlib.md5(f"{date.today()}:{recipe_id}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class DiscoverService:
    """发现服务类"""

    def __init__(self, repository: DiscoverRepository):
        self.repository = repository

    def today_recommend(self, household_id: str, limit: int = 6) -> DiscoverResponse:
        """今日推荐：cooked×2 + 收藏×3 + 按日固定随机种子；取 top(n-2) + 随机探索 2 条"""
        limit = max(2, int(limit))
        candidates = self.repository.get_all_with_stats(household_id)

        def score(r):
            return (r._cooked_count or 0) * 2 + (3 if r._is_favorited else 0) + _daily_rand(r.id)

        scored = sorted(candidates, key=score, reverse=True)
        top_n = max(limit - 2, 0)
        top = scored[:top_n]
        rest = scored[top_n:]
        random.shuffle(rest)  # 随机探索：每次刷新变化
        result = top + rest[:2]
        return DiscoverResponse(list=[self._to_item(r) for r in result])

    def hot_recipes(self, household_id: str, limit: int = 6) -> DiscoverResponse:
        """热门：做过次数×2 + 收藏×3"""
        recipes = self.repository.get_all_with_stats(household_id)
        scored = sorted(recipes, key=lambda r: (r._cooked_count or 0) * 2 + (3 if r._is_favorited else 0), reverse=True)
        return DiscoverResponse(list=[self._to_item(r) for r in scored[:limit]])

    def new_recipes(self, limit: int = 6) -> DiscoverResponse:
        """最新"""
        recipes = self.repository.get_new_recipes(limit)
        return DiscoverResponse(list=[self._to_item(r) for r in recipes])

    def random_recipes(self, limit: int = 6) -> DiscoverResponse:
        """随机"""
        recipes = self.repository.get_random_recipes(limit)
        return DiscoverResponse(list=[self._to_item(r) for r in recipes])

    @staticmethod
    def _to_item(r) -> DiscoverRecipe:
        return DiscoverRecipe(
            id=r.id,
            title=r.title,
            cover=r.cover,
            summary=r.summary,
            cook_time=((r.prep_minutes or 0) + (r.cook_minutes or 0)) or None,
            is_favorited=bool(getattr(r, "_is_favorited", False)),
            is_in_today_menu=bool(getattr(r, "_is_in_today_menu", False)),
            cooked_count=int(getattr(r, "_cooked_count", 0)),
        )
