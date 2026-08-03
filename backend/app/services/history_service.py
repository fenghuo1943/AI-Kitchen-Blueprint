"""浏览历史业务逻辑层"""
from app.repositories.history_repository import HistoryRepository
from app.schemas.history import HistoryResponse, HistoryListResponse


class HistoryService:
    """浏览历史服务类"""

    def __init__(self, repository: HistoryRepository):
        self.repository = repository

    def list_history(self, household_id: str, page: int = 1, page_size: int = 30) -> HistoryListResponse:
        """历史列表"""
        offset = (page - 1) * page_size
        items = self.repository.get_by_household(household_id, offset, page_size)
        total = self.repository.count_by_household(household_id)
        return HistoryListResponse(
            data=[HistoryResponse(**item) for item in items],
            total=total, page=page, page_size=page_size
        )

    def record(self, household_id: str, recipe_id: str) -> None:
        """记录历史"""
        self.repository.record(household_id, recipe_id)

    def remove_one(self, household_id: str, recipe_id: str) -> bool:
        """删除单条历史"""
        return self.repository.delete_one(household_id, recipe_id)

    def clear(self, household_id: str) -> int:
        """清空全部历史"""
        return self.repository.clear(household_id)
