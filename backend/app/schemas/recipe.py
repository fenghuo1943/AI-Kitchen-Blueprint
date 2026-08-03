from pydantic import BaseModel, Field
from typing import List, Optional


class IngredientInput(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None


class RecipeCreate(BaseModel):
    title: str = Field(min_length=1)
    summary: Optional[str] = None
    servings: Optional[int] = None
    prep_minutes: Optional[int] = None
    cook_minutes: Optional[int] = None
    difficulty: Optional[str] = None
    ingredients: List[IngredientInput] = []
    steps: List[str] = []
    tags: List[str] = []
