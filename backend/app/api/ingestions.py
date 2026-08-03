"""入库任务 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.ingestion_repository import IngestionRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.services.ingestion_service import IngestionService
from app.schemas.ingestion import (
    IngestionCreate, IngestionResponse, IngestionListResponse, IngestionDetailResponse
)

router = APIRouter(prefix="/ingestions", tags=["入库管理"])


def get_ingestion_service(db: Session = Depends(get_db)) -> IngestionService:
    """获取入库服务实例"""
    ingestion_repo = IngestionRepository(db)
    ingredient_repo = IngredientRepository(db)
    return IngestionService(ingestion_repo, ingredient_repo)


@router.post("", response_model=IngestionResponse, status_code=201)
def create_ingestion(
    data: IngestionCreate,
    service: IngestionService = Depends(get_ingestion_service)
):
    """创建入库任务"""
    try:
        return service.create_job(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=IngestionListResponse)
def list_ingestions(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: IngestionService = Depends(get_ingestion_service)
):
    """获取入库任务列表"""
    return service.list_jobs(status=status, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=IngestionDetailResponse)
def get_ingestion(
    job_id: str,
    service: IngestionService = Depends(get_ingestion_service)
):
    """获取入库任务详情"""
    result = service.get_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="入库任务不存在")
    return result
