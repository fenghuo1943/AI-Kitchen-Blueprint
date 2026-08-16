"""食材管理 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.ingredient_repository import IngredientRepository
from app.services.ingredient_service import IngredientService
from app.schemas.batch import BatchDeleteRequest, BatchDeleteResponse
from app.schemas.ingredient import (
    IngredientCreate, IngredientUpdate, IngredientResponse,
    IngredientListResponse, IngredientSearchRequest
)

router = APIRouter(prefix="/ingredients", tags=["食材管理"])


def get_ingredient_service(db: Session = Depends(get_db)) -> IngredientService:
    """获取食材服务实例"""
    repository = IngredientRepository(db)
    return IngredientService(repository)


@router.get("", response_model=IngredientListResponse)
def list_ingredients(
    query: Optional[str] = Query(None, description="搜索关键词"),
    category_id: Optional[str] = Query(None, description="食材分类ID筛选"),
    deleted: bool = Query(False, description="是否查询回收站（已删除）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: IngredientService = Depends(get_ingredient_service)
):
    """获取食材列表"""
    if deleted:
        return service.list_deleted(page=page, page_size=page_size)
    request = IngredientSearchRequest(query=query, category_id=category_id)
    return service.search_ingredients(request, page=page, page_size=page_size)


@router.post("/batch-delete", response_model=BatchDeleteResponse)
def batch_delete_ingredients(
    data: BatchDeleteRequest,
    service: IngredientService = Depends(get_ingredient_service)
):
    """批量彻底删除回收站中的食材（尽力而为：被菜谱/库存引用的跳过并返回失败项）"""
    return service.hard_delete_many(data.ids)


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(
    ingredient_id: str,
    service: IngredientService = Depends(get_ingredient_service)
):
    """获取食材详情"""
    result = service.get_ingredient(ingredient_id)
    if not result:
        raise HTTPException(status_code=404, detail="食材不存在")
    return result


@router.post("", response_model=IngredientResponse, status_code=201)
def create_ingredient(
    data: IngredientCreate,
    service: IngredientService = Depends(get_ingredient_service)
):
    """创建食材"""
    try:
        return service.create_ingredient(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: str,
    data: IngredientUpdate,
    service: IngredientService = Depends(get_ingredient_service)
):
    """更新食材"""
    result = service.update_ingredient(ingredient_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="食材不存在")
    return result


@router.delete("/{ingredient_id}", status_code=204)
def delete_ingredient(
    ingredient_id: str,
    forever: bool = Query(False, description="true=彻底删除（回收站），false=软删除入回收站"),
    service: IngredientService = Depends(get_ingredient_service)
):
    """删除食材（被菜谱使用时不允删除）"""
    try:
        if forever:
            ok = service.hard_delete_ingredient(ingredient_id)
        else:
            ok = service.delete_ingredient(ingredient_id)
        if not ok:
            raise HTTPException(status_code=404, detail="食材不存在")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return None


@router.post("/{ingredient_id}/restore", response_model=IngredientResponse)
def restore_ingredient(
    ingredient_id: str,
    service: IngredientService = Depends(get_ingredient_service)
):
    """从回收站恢复食材"""
    try:
        result = service.restore_ingredient(ingredient_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="食材不存在")
    return result


@router.post("/{ingredient_id}/aliases", status_code=201)
def add_alias(
    ingredient_id: str,
    alias_name: str = Query(..., description="别名"),
    service: IngredientService = Depends(get_ingredient_service)
):
    """添加食材别名"""
    try:
        result = service.add_alias(ingredient_id, alias_name)
        if not result:
            raise HTTPException(status_code=404, detail="食材不存在")
        return {"id": result.id, "alias": result.alias}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/aliases/{alias_id}", status_code=204)
def remove_alias(
    alias_id: str,
    service: IngredientService = Depends(get_ingredient_service)
):
    """删除食材别名"""
    if not service.remove_alias(alias_id):
        raise HTTPException(status_code=404, detail="别名不存在")
    return None
