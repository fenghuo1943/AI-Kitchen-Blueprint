"""调料数据访问层"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models import Seasoning, SeasoningCategory


class SeasoningRepository:
    """调料仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, seasoning_id: str) -> Optional[Seasoning]:
        """根据ID获取调料（排除已删除）"""
        return self.db.query(Seasoning).filter(
            Seasoning.id == seasoning_id,
            Seasoning.deleted_at.is_(None)
        ).first()

    def get_by_name(self, name: str) -> Optional[Seasoning]:
        """根据名称获取调料"""
        return self.db.query(Seasoning).filter(Seasoning.canonical_name == name).first()

    def search(
        self,
        query: Optional[str] = None,
        category_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Seasoning], int]:
        """搜索调料"""
        stmt = self.db.query(Seasoning).filter(Seasoning.deleted_at.is_(None))

        # 关键词（名称或拼音前缀）
        if query:
            search_filter = or_(
                Seasoning.canonical_name.contains(query),
                Seasoning.pinyin.like(f"{query}%")
            )
            stmt = stmt.filter(search_filter)

        # 分类筛选
        if category_id:
            stmt = stmt.filter(Seasoning.category_id == category_id)

        total = stmt.count()

        offset = (page - 1) * page_size
        seasonings = stmt.offset(offset).limit(page_size).all()
        return seasonings, total

    def list_all(self) -> List[Seasoning]:
        """获取全部调料（按分类、拼音排序）"""
        return self.db.query(Seasoning).filter(
            Seasoning.deleted_at.is_(None)
        ).order_by(Seasoning.category_id, Seasoning.pinyin).all()

    def create(self, seasoning: Seasoning) -> Seasoning:
        """创建调料"""
        self.db.add(seasoning)
        self.db.commit()
        self.db.refresh(seasoning)
        return seasoning

    def update(self, seasoning: Seasoning) -> Seasoning:
        """更新调料"""
        self.db.commit()
        self.db.refresh(seasoning)
        return seasoning

    def soft_delete(self, seasoning_id: str) -> bool:
        """软删除调料"""
        seasoning = self.get_by_id(seasoning_id)
        if not seasoning:
            return False
        from datetime import datetime
        seasoning.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def get_category_name(self, category_id: Optional[str]) -> Optional[str]:
        """获取调料分类名称"""
        if not category_id:
            return None
        cat = self.db.query(SeasoningCategory).filter(SeasoningCategory.id == category_id).first()
        return cat.name if cat else None
