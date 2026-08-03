"""分类管理 API 路由（type=recipe|ingredient|seasoning）"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.category_service import CategoryService
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse
)

router = APIRouter(prefix="/categories", tags=["分类管理"])

VALID_TYPES = ("recipe", "ingredient", "seasoning")


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    """获取分类服务实例"""
    return CategoryService(db)


@router.get("", response_model=CategoryListResponse)
def list_categories(
    type_: str = Query("recipe", alias="type", pattern="^(recipe|ingredient|seasoning)$", description="分类类型"),
    service: CategoryService = Depends(get_category_service)
):
    """获取分类列表"""
    return service.list_categories(type_)


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreate,
    type_: str = Query("recipe", alias="type", pattern="^(recipe|ingredient|seasoning)$", description="分类类型"),
    service: CategoryService = Depends(get_category_service)
):
    """创建分类"""
    try:
        return service.create_category(type_, data.name, data.parent_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str,
    data: CategoryUpdate,
    type_: str = Query("recipe", alias="type", pattern="^(recipe|ingredient|seasoning)$", description="分类类型"),
    service: CategoryService = Depends(get_category_service)
):
    """更新分类"""
    try:
        result = service.update_category(
            type_, category_id, name=data.name, parent_id=data.parent_id, sort_order=data.sort_order
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="分类不存在")
    return result


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    type_: str = Query("recipe", alias="type", pattern="^(recipe|ingredient|seasoning)$", description="分类类型"),
    service: CategoryService = Depends(get_category_service)
):
    """删除分类（默认分类不可删除；被引用时拒绝）"""
    try:
        if not service.delete_category(type_, category_id):
            raise HTTPException(status_code=404, detail="分类不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None
