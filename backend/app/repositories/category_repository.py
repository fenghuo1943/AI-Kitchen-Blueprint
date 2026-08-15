"""分类数据访问层（菜谱/食材/调料分类，按 type 分发到对应表）"""
from typing import Optional, List, Type
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import RecipeCategory, IngredientCategory, SeasoningCategory

# 默认分类受保护，不可删除/重命名
# ID '1' 为种子/测试环境约定；生产库默认分类可能为 UUID，按名称 '默认' 解析。
DEFAULT_CATEGORY_ID = "1"
DEFAULT_CATEGORY_NAME = "默认"

CATEGORY_MODELS: dict[str, Type] = {
    "recipe": RecipeCategory,
    "ingredient": IngredientCategory,
    "seasoning": SeasoningCategory,
}


def get_default_category_id(db: Session, type_: str) -> str:
    """解析某类型的默认分类 ID。

    优先按名称 '默认' 找到对应分类（生产库默认分类为 UUID）；
    找不到时回落 DEFAULT_CATEGORY_ID（种子/测试库约定 id='1'）。
    入库时未指定分类的菜谱/食材/调料统一落到该分类。
    """
    model = CATEGORY_MODELS.get(type_)
    if not model:
        raise ValueError(f"未知分类类型: {type_}")
    cat = db.query(model).filter(model.name == DEFAULT_CATEGORY_NAME).first()
    return cat.id if cat else DEFAULT_CATEGORY_ID


class CategoryRepository:
    """分类仓储类"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _model(type_: str):
        model = CATEGORY_MODELS.get(type_)
        if not model:
            raise ValueError(f"未知分类类型: {type_}")
        return model

    def list(self, type_: str) -> List:
        """分类列表"""
        model = self._model(type_)
        order = model.sort_order if hasattr(model, "sort_order") else model.id
        return self.db.query(model).filter(
            model.deleted_at.is_(None)
        ).order_by(order, model.created_at).all()

    def get(self, type_: str, category_id: str):
        """根据ID获取分类（排除已删除）"""
        model = self._model(type_)
        return self.db.query(model).filter(
            model.id == category_id,
            model.deleted_at.is_(None)
        ).first()

    def get_by_name(self, type_: str, name: str):
        """根据名称获取分类"""
        model = self._model(type_)
        return self.db.query(model).filter(model.name == name).first()

    def create(self, type_: str, name: str, parent_id: Optional[str] = None, sort_order: int = 0):
        """创建分类（同名唯一校验由数据库约束保证，调用方捕获冲突）"""
        model = self._model(type_)
        obj = model(name=name)
        if hasattr(model, "parent_id") and parent_id:
            obj.parent_id = parent_id
        if hasattr(model, "sort_order"):
            obj.sort_order = sort_order
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, type_: str, category_id: str, name: Optional[str] = None,
               parent_id: Optional[str] = None, sort_order: Optional[int] = None):
        """更新分类（默认分类不可重命名）"""
        model = self._model(type_)
        obj = self.get(type_, category_id)
        if not obj:
            return None
        if name and name != obj.name and (
            category_id == DEFAULT_CATEGORY_ID or obj.name == DEFAULT_CATEGORY_NAME
        ):
            raise ValueError("默认分类不可重命名")
        if name:
            obj.name = name
        if hasattr(model, "parent_id") and parent_id is not None:
            if category_id == parent_id:
                raise ValueError("父分类不能是自身")
            obj.parent_id = parent_id or None
        if hasattr(model, "sort_order") and sort_order is not None:
            obj.sort_order = sort_order
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, type_: str, category_id: str) -> bool:
        """删除分类（默认分类不可删除；被引用时由外键约束保护）"""
        if category_id == DEFAULT_CATEGORY_ID:
            raise ValueError("默认分类不可删除")
        obj = self.get(type_, category_id)
        if not obj:
            return False
        if obj.name == DEFAULT_CATEGORY_NAME:
            raise ValueError("默认分类不可删除")
        self.db.delete(obj)
        self.db.commit()
        return True

    def count_recipes(self, category_id: str) -> int:
        """统计某菜谱分类被引用的菜谱数"""
        from app.db.models import RecipeCategoryLink
        return self.db.query(RecipeCategoryLink).filter(
            RecipeCategoryLink.category_id == category_id
        ).count()
