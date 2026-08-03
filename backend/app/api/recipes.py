from fastapi import APIRouter

from app.schemas.recipe import RecipeCreate
from app.services.recommendation_service import build_recommendation_payload

router = APIRouter(prefix="/api/v1", tags=["recipes"])


@router.get("/recipes")
def list_recipes():
    return {"data": [], "meta": {"page": 1, "page_size": 20}}


@router.post("/recipes", status_code=201)
def create_recipe(payload: RecipeCreate):
    return {"data": {"id": "recipe_001", "status": "draft", "revision": 1, **payload.model_dump()}, "meta": {}}


@router.post("/recommendations")
def get_recommendations():
    return build_recommendation_payload(["鸡蛋", "番茄"])
