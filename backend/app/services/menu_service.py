"""每日菜单业务逻辑层"""
from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import (
    MenuByDateResponse, MonthDatesResponse, WaterfallResponse,
    WaterfallGroup, MealPlanItem,
)


class MenuService:
    """菜单服务类"""

    def __init__(self, repository: MenuRepository):
        self.repository = repository

    def add(self, household_id: str, recipe_id: str, date: str) -> bool:
        """添加菜谱到某天"""
        if not date:
            raise ValueError("日期不能为空")
        return self.repository.add(household_id, recipe_id, date)

    def remove(self, household_id: str, recipe_id: str, date: str) -> bool:
        """删除某天某菜谱"""
        return self.repository.remove(household_id, recipe_id, date)

    def get_by_date(self, household_id: str, date: str) -> MenuByDateResponse:
        """某天菜单（含食材/调料聚合）"""
        return MenuByDateResponse(
            date=date,
            list=[MealPlanItem(**item) for item in self.repository.get_by_date(household_id, date)],
            ing_list=self.repository.get_ingredients_by_date(household_id, date),
            sea_list=self.repository.get_seasonings_by_date(household_id, date),
        )

    def get_month_dates(self, household_id: str, month: str) -> MonthDatesResponse:
        """某月有菜单的日期"""
        return MonthDatesResponse(dates=self.repository.get_dates_by_month(household_id, month))

    def get_waterfall(self, household_id: str, page: int, page_size: int) -> WaterfallResponse:
        """瀑布流：按天分组"""
        dates = self.repository.get_dates_paginated(household_id, page, page_size)
        rows = self.repository.get_by_dates(household_id, dates)
        total_page = (self.repository.count_dates(household_id) + page_size - 1) // page_size

        grouped = {}
        for row in rows:
            d = row["date"]
            grouped.setdefault(d, []).append(MealPlanItem(
                recipe_id=row["recipe_id"],
                title=row["title"],
                cover=row["cover"],
                cook_time=row["cook_time"],
                added_at=row["added_at"],
            ))

        return WaterfallResponse(
            list=[WaterfallGroup(date=d, recipes=recipes) for d, recipes in grouped.items()],
            total_page=total_page,
            page=page,
            page_size=page_size,
        )
