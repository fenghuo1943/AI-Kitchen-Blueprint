"""分类业务逻辑层"""
from typing import Optional, List
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryResponse, CategoryListResponse
from app.db.models import RecipeCategoryLink, Ingredient, Seasoning


class CategoryService:
    """分类服务类"""

    def __init__(self, db: Session):
        self.repository = CategoryRepository(db)
        self.db = db

    def list_categories(self, type_: str) -> CategoryListResponse:
        """分类列表"""
        categories = self.repository.list(type_)
        return CategoryListResponse(
            data=[self._to_response(c) for c in categories],
            total=len(categories)
        )

    def create_category(self, type_: str, name: str, parent_id: Optional[str] = None) -> CategoryResponse:
        """创建分类"""
        if not name.strip():
            raise ValueError("分类名称不能为空")
        try:
            obj = self.repository.create(type_, name.strip(), parent_id=parent_id)
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("分类名称已存在") from e
        return self._to_response(obj)

    def update_category(self, type_: str, category_id: str, name: Optional[str] = None,
                        parent_id: Optional[str] = None, sort_order: Optional[int] = None) -> Optional[CategoryResponse]:
        """更新分类"""
        try:
            obj = self.repository.update(type_, category_id, name=name, parent_id=parent_id, sort_order=sort_order)
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("分类名称已存在") from e
        if not obj:
            return None
        return self._to_response(obj)

    def delete_category(self, type_: str, category_id: str) -> bool:
        """删除分类"""
        obj = self.repository.get(type_, category_id)
        if not obj:
            return False
        # 被引用检查：菜谱分类被菜谱引用、食材分类被食材引用、调料分类被调料引用
        if type_ == "recipe":
            if self.db.query(RecipeCategoryLink).filter(RecipeCategoryLink.category_id == category_id).count() > 0:
                raise ValueError("该分类下还有菜谱，无法删除")
        elif type_ == "ingredient":
            if self.db.query(Ingredient).filter(Ingredient.category_id == category_id).count() > 0:
                raise ValueError("该分类下还有食材，无法删除")
        elif type_ == "seasoning":
            if self.db.query(Seasoning).filter(Seasoning.category_id == category_id).count() > 0:
                raise ValueError("该分类下还有调料，无法删除")
        return self.repository.delete(type_, category_id)

    @staticmethod
    def _to_response(obj) -> CategoryResponse:
        return CategoryResponse(
            id=obj.id,
            name=obj.name,
            parent_id=getattr(obj, "parent_id", None),
            sort_order=getattr(obj, "sort_order", 0),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
