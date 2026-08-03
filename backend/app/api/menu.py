"""每日菜单 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.menu_repository import MenuRepository
from app.repositories.recipe_repository import RecipeRepository
from app.services.menu_service import MenuService
from app.schemas.menu import (
    MealPlanCreate, MenuByDateResponse, MonthDatesResponse, WaterfallResponse
)

router = APIRouter(prefix="/menu", tags=["每日菜单"])


def get_menu_service(db: Session = Depends(get_db)) -> MenuService:
    """获取菜单服务实例"""
    return MenuService(MenuRepository(db))


@router.get("", response_model=dict)
def get_menu(
    household_id: str = Query(..., description="家庭ID"),
    date_: str = Query(None, alias="date", description="日期 YYYY-MM-DD（单日模式）"),
    month: str = Query(None, description="月份 YYYY-MM（返回该月有菜单的日期）"),
    mode: str = Query(None, description="waterfall=瀑布流模式"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    service: MenuService = Depends(get_menu_service)
):
    """菜单查询（单日 / 月份 / 瀑布流）"""
    if mode == "waterfall":
        return service.get_waterfall(household_id, page, page_size).model_dump()
    if month:
        return service.get_month_dates(household_id, month).model_dump()
    if date_:
        return service.get_by_date(household_id, date_).model_dump()
    # 默认今天
    from datetime import date
    return service.get_by_date(household_id, date.today().isoformat()).model_dump()


@router.post("", status_code=201)
def add_to_menu(
    data: MealPlanCreate,
    household_id: str = Query(..., description="家庭ID"),
    db: Session = Depends(get_db),
    service: MenuService = Depends(get_menu_service)
):
    """添加菜谱到某天"""
    recipe_repo = RecipeRepository(db)
    if not recipe_repo.get_by_id(data.recipe_id):
        raise HTTPException(status_code=404, detail="菜谱不存在")
    try:
        added = service.add(household_id, data.recipe_id, data.date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not added:
        raise HTTPException(status_code=409, detail=f"{data.date} 已存在该菜谱")
    return {"message": "已添加到菜单"}


@router.delete("/{recipe_id}", status_code=204)
def remove_from_menu(
    recipe_id: str,
    date_: str = Query(..., alias="date", description="日期 YYYY-MM-DD"),
    household_id: str = Query(..., description="家庭ID"),
    service: MenuService = Depends(get_menu_service)
):
    """删除某天某菜谱"""
    if not service.remove(household_id, recipe_id, date_):
        raise HTTPException(status_code=404, detail="菜单中不存在该菜谱")
    return None
