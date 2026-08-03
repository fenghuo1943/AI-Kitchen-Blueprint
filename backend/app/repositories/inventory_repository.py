"""库存数据访问层"""
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import InventoryItem, Household


class InventoryRepository:
    """库存仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: str) -> Optional[InventoryItem]:
        """根据ID获取库存物品"""
        return self.db.query(InventoryItem).filter(
            InventoryItem.id == item_id,
            InventoryItem.deleted_at.is_(None)
        ).first()

    def search(
        self,
        household_id: str,
        ingredient_id: Optional[str] = None,
        include_expired: bool = False,
        expires_within_days: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryItem], int]:
        """搜索库存物品"""
        stmt = self.db.query(InventoryItem).filter(
            InventoryItem.household_id == household_id,
            InventoryItem.deleted_at.is_(None)
        )

        # 食材筛选
        if ingredient_id:
            stmt = stmt.filter(InventoryItem.ingredient_id == ingredient_id)

        # 过期筛选
        if not include_expired:
            stmt = stmt.filter(InventoryItem.is_expired == 0)

        # 即将过期筛选
        if expires_within_days is not None:
            cutoff_date = datetime.utcnow() + timedelta(days=expires_within_days)
            stmt = stmt.filter(
                and_(
                    InventoryItem.expires_at.isnot(None),
                    InventoryItem.expires_at <= cutoff_date,
                    InventoryItem.expires_at > datetime.utcnow()
                )
            )

        # 统计总数
        total = stmt.count()

        # 分页
        offset = (page - 1) * page_size
        items = stmt.offset(offset).limit(page_size).all()

        return items, total

    def create(self, item: InventoryItem) -> InventoryItem:
        """创建库存物品"""
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, item: InventoryItem) -> InventoryItem:
        """更新库存物品"""
        self.db.commit()
        self.db.refresh(item)
        return item

    def soft_delete(self, item_id: str) -> bool:
        """软删除库存物品"""
        item = self.get_by_id(item_id)
        if not item:
            return False
        item.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def check_expiry(self, item_id: str) -> Optional[InventoryItem]:
        """检查物品是否过期"""
        item = self.get_by_id(item_id)
        if not item or not item.expires_at:
            return item

        if item.expires_at < datetime.utcnow() and item.is_expired == 0:
            item.is_expired = 1
            self.db.commit()
            self.db.refresh(item)

        return item

    def get_expiring_soon(self, household_id: str, days: int = 7) -> List[InventoryItem]:
        """获取即将过期的物品"""
        cutoff_date = datetime.utcnow() + timedelta(days=days)
        return self.db.query(InventoryItem).filter(
            InventoryItem.household_id == household_id,
            InventoryItem.deleted_at.is_(None),
            InventoryItem.is_expired == 0,
            InventoryItem.expires_at.isnot(None),
            InventoryItem.expires_at <= cutoff_date,
            InventoryItem.expires_at > datetime.utcnow()
        ).all()

    def get_household(self, household_id: str) -> Optional[Household]:
        """获取家庭信息"""
        return self.db.query(Household).filter(Household.id == household_id).first()

    def list_households(self, page: int = 1, page_size: int = 20) -> Tuple[List[Household], int]:
        """获取家庭列表"""
        stmt = self.db.query(Household)
        total = stmt.count()
        offset = (page - 1) * page_size
        households = stmt.offset(offset).limit(page_size).all()
        return households, total

    def create_household(self, household: Household) -> Household:
        """创建家庭"""
        self.db.add(household)
        self.db.commit()
        self.db.refresh(household)
        return household
