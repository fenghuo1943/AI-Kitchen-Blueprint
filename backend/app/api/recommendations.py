"""推荐 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendation import (
    RecommendationRequest, RecommendationResponse,
    IngredientCoverageRequest, IngredientCoverageResponse
)

router = APIRouter(prefix="/recommendations", tags=["推荐引擎"])


def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    """获取推荐服务实例"""
    repository = RecommendationRepository(db)
    return RecommendationService(repository)


@router.post("", response_model=RecommendationResponse)
def get_recommendations(
    request: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service)
):
    """获取菜谱推荐"""
    return service.get_recommendations(request)


@router.post("/coverage", response_model=IngredientCoverageResponse)
def calculate_coverage(
    request: IngredientCoverageRequest,
    service: RecommendationService = Depends(get_recommendation_service)
):
    """计算菜谱的食材覆盖率"""
    try:
        return service.calculate_coverage(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
