"""菜谱管理 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.services.recipe_service import RecipeService
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeResponse,
    RecipeListResponse, RecipeSearchRequest
)

router = APIRouter(prefix="/recipes", tags=["菜谱管理"])


def get_recipe_service(db: Session = Depends(get_db)) -> RecipeService:
    """获取菜谱服务实例"""
    recipe_repo = RecipeRepository(db)
    ingredient_repo = IngredientRepository(db)
    return RecipeService(recipe_repo, ingredient_repo)


@router.get("", response_model=RecipeListResponse)
def list_recipes(
    query: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="状态筛选"),
    difficulty: Optional[str] = Query(None, description="难度筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: RecipeService = Depends(get_recipe_service)
):
    """获取菜谱列表"""
    request = RecipeSearchRequest(query=query, status=status, difficulty=difficulty)
    return service.search_recipes(request, page=page, page_size=page_size)


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: str,
    service: RecipeService = Depends(get_recipe_service)
):
    """获取菜谱详情"""
    result = service.get_recipe(recipe_id)
    if not result:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return result


@router.post("", response_model=RecipeResponse, status_code=201)
def create_recipe(
    data: RecipeCreate,
    service: RecipeService = Depends(get_recipe_service)
):
    """创建菜谱草稿"""
    return service.create_recipe(data)


@router.patch("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: str,
    data: RecipeUpdate,
    service: RecipeService = Depends(get_recipe_service)
):
    """更新菜谱"""
    result = service.update_recipe(recipe_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return result


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(
    recipe_id: str,
    service: RecipeService = Depends(get_recipe_service)
):
    """删除菜谱"""
    if not service.delete_recipe(recipe_id):
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return None


@router.post("/{recipe_id}/publish", response_model=RecipeResponse)
def publish_recipe(
    recipe_id: str,
    service: RecipeService = Depends(get_recipe_service)
):
    """发布菜谱"""
    result = service.publish_recipe(recipe_id)
    if not result:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return result
