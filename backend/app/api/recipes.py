"""菜谱管理 API 路由"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.services.recipe_service import RecipeService
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeResponse,
    RecipeListResponse
)

router = APIRouter(prefix="/recipes", tags=["菜谱管理"])


def get_recipe_service(db: Session = Depends(get_db)) -> RecipeService:
    """获取菜谱服务实例"""
    recipe_repo = RecipeRepository(db)
    ingredient_repo = IngredientRepository(db)
    return RecipeService(recipe_repo, ingredient_repo)


@router.get("", response_model=RecipeListResponse)
def list_recipes(
    query: Optional[str] = Query(None, description="搜索关键词（q 别名）"),
    q: Optional[str] = Query(None, description="搜索关键词（cook 兼容别名）"),
    status: Optional[str] = Query(None, description="状态筛选"),
    difficulty: Optional[str] = Query(None, description="难度筛选"),
    tags: Optional[str] = Query(None, description="标签（逗号分隔）"),
    max_cook_time: Optional[int] = Query(None, description="最大烹饪时间（分钟）"),
    ingredients: Optional[str] = Query(None, description="食材ID（逗号分隔）"),
    match: str = Query("any", pattern="^(exact|any)$", description="食材匹配模式 exact=全含 any=任一"),
    category_id: Optional[str] = Query(None, description="菜谱分类ID"),
    household_id: Optional[str] = Query(None, description="家庭ID（用于收藏/菜单状态）"),
    sort: str = Query("score", description="排序: score综合 date最新 title名称 cook做过次数 random随机"),
    order: str = Query("desc", description="排序方向 asc/desc"),
    deleted: bool = Query(False, description="是否查询回收站（已删除）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: RecipeService = Depends(get_recipe_service)
):
    """获取菜谱列表（支持多条件筛选）"""
    keyword = q or query
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    ing_list = [i for i in ingredients.split(",")] if ingredients else None
    return service.search_recipes(
        query=keyword,
        status=status,
        difficulty=difficulty,
        tags=tag_list,
        max_cook_time=max_cook_time,
        ingredients=ing_list,
        match=match,
        category_id=category_id,
        household_id=household_id,
        sort=sort,
        order=order,
        deleted=deleted,
        page=page,
        page_size=page_size
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: str,
    household_id: Optional[str] = Query(None, description="家庭ID（记录浏览历史并返回收藏/菜单状态）"),
    service: RecipeService = Depends(get_recipe_service)
):
    """获取菜谱详情（打开即记录浏览历史）"""
    result = service.get_recipe(recipe_id, household_id=household_id)
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
    """更新菜谱（支持食材/步骤/调料/分类/标签完整编辑）"""
    result = service.update_recipe(recipe_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return result


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(
    recipe_id: str,
    forever: bool = Query(False, description="true=彻底删除（回收站），false=软删除入回收站"),
    service: RecipeService = Depends(get_recipe_service)
):
    """删除菜谱"""
    if forever:
        if not service.hard_delete_recipe(recipe_id):
            raise HTTPException(status_code=404, detail="菜谱不存在")
    else:
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


@router.post("/{recipe_id}/restore", response_model=RecipeResponse)
def restore_recipe(
    recipe_id: str,
    service: RecipeService = Depends(get_recipe_service)
):
    """从回收站恢复菜谱"""
    result = service.restore_recipe(recipe_id)
    if not result:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return result
