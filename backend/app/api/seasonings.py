"""调料管理 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.seasoning_service import SeasoningService
from app.schemas.batch import BatchDeleteRequest, BatchDeleteResponse
from app.schemas.seasoning import (
    SeasoningCreate, SeasoningUpdate, SeasoningResponse, SeasoningListResponse
)

router = APIRouter(prefix="/seasonings", tags=["调料管理"])


def get_seasoning_service(db: Session = Depends(get_db)) -> SeasoningService:
    """获取调料服务实例"""
    return SeasoningService(db)


@router.get("", response_model=SeasoningListResponse)
def list_seasonings(
    query: Optional[str] = Query(None, description="搜索关键词（名称或拼音）"),
    category_id: Optional[str] = Query(None, description="分类筛选"),
    deleted: bool = Query(False, description="是否查询回收站（已删除）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SeasoningService = Depends(get_seasoning_service)
):
    """获取调料列表"""
    if deleted:
        return service.list_deleted(page=page, page_size=page_size)
    return service.search_seasonings(query=query, category_id=category_id, page=page, page_size=page_size)


@router.post("/batch-delete", response_model=BatchDeleteResponse)
def batch_delete_seasonings(
    data: BatchDeleteRequest,
    service: SeasoningService = Depends(get_seasoning_service)
):
    """批量彻底删除回收站中的调料（尽力而为：被菜谱引用的跳过并返回失败项）"""
    return service.hard_delete_many(data.ids)


@router.get("/all", response_model=SeasoningListResponse)
def list_all_seasonings(service: SeasoningService = Depends(get_seasoning_service)):
    """获取全部调料（无分页，用于选择器）"""
    seasonings = service.repository.list_all()
    from app.schemas.seasoning import SeasoningListResponse
    return SeasoningListResponse(
        data=[service._to_response(s) for s in seasonings],
        total=len(seasonings), page=1, page_size=len(seasonings) or 1
    )


@router.get("/{seasoning_id}", response_model=SeasoningResponse)
def get_seasoning(
    seasoning_id: str,
    service: SeasoningService = Depends(get_seasoning_service)
):
    """获取调料详情"""
    result = service.get_seasoning(seasoning_id)
    if not result:
        raise HTTPException(status_code=404, detail="调料不存在")
    return result


@router.post("", response_model=SeasoningResponse, status_code=201)
def create_seasoning(
    data: SeasoningCreate,
    service: SeasoningService = Depends(get_seasoning_service)
):
    """创建调料"""
    try:
        return service.create_seasoning(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{seasoning_id}", response_model=SeasoningResponse)
def update_seasoning(
    seasoning_id: str,
    data: SeasoningUpdate,
    service: SeasoningService = Depends(get_seasoning_service)
):
    """更新调料"""
    try:
        result = service.update_seasoning(seasoning_id, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="调料不存在")
    return result


@router.delete("/{seasoning_id}", status_code=204)
def delete_seasoning(
    seasoning_id: str,
    forever: bool = Query(False, description="true=彻底删除（回收站），false=软删除入回收站"),
    service: SeasoningService = Depends(get_seasoning_service)
):
    """删除调料（被菜谱使用时不允删除）"""
    try:
        if forever:
            ok = service.hard_delete_seasoning(seasoning_id)
        else:
            ok = service.delete_seasoning(seasoning_id)
        if not ok:
            raise HTTPException(status_code=404, detail="调料不存在")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return None


@router.post("/{seasoning_id}/restore", response_model=SeasoningResponse)
def restore_seasoning(
    seasoning_id: str,
    service: SeasoningService = Depends(get_seasoning_service)
):
    """从回收站恢复调料"""
    try:
        result = service.restore_seasoning(seasoning_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="调料不存在")
    return result
