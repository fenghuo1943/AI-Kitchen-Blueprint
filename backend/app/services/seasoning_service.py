"""调料业务逻辑层"""
import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pinyin import to_pinyin
from app.db.models import Seasoning
from app.repositories.seasoning_repository import SeasoningRepository
from app.schemas.seasoning import (
    SeasoningCreate, SeasoningUpdate, SeasoningResponse, SeasoningListResponse
)


class SeasoningService:
    """调料服务类"""

    def __init__(self, db: Session):
        self.repository = SeasoningRepository(db)
        self.db = db

    def search_seasonings(self, query: Optional[str] = None, category_id: Optional[str] = None,
                          page: int = 1, page_size: int = 20) -> SeasoningListResponse:
        """搜索调料"""
        seasonings, total = self.repository.search(
            query=query, category_id=category_id, page=page, page_size=page_size
        )
        return SeasoningListResponse(
            data=[self._to_response(s) for s in seasonings],
            total=total, page=page, page_size=page_size
        )

    def get_seasoning(self, seasoning_id: str) -> Optional[SeasoningResponse]:
        """获取调料详情"""
        seasoning = self.repository.get_by_id(seasoning_id)
        if not seasoning:
            return None
        return self._to_response(seasoning)

    def create_seasoning(self, data: SeasoningCreate) -> SeasoningResponse:
        """创建调料"""
        name = data.canonical_name.strip()
        if not name:
            raise ValueError("调料名称不能为空")
        seasoning = Seasoning(
            id=str(uuid.uuid4()),
            canonical_name=name,
            pinyin=to_pinyin(name),
            category_id=data.category_id,
        )
        try:
            seasoning = self.repository.create(seasoning)
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("调料名称已存在") from e
        return self._to_response(seasoning)

    def update_seasoning(self, seasoning_id: str, data: SeasoningUpdate) -> Optional[SeasoningResponse]:
        """更新调料"""
        seasoning = self.repository.get_by_id(seasoning_id)
        if not seasoning:
            return None
        if data.canonical_name is not None:
            name = data.canonical_name.strip()
            if not name:
                raise ValueError("调料名称不能为空")
            seasoning.canonical_name = name
            seasoning.pinyin = to_pinyin(name)
        if data.category_id is not None:
            seasoning.category_id = data.category_id
        try:
            seasoning = self.repository.update(seasoning)
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("调料名称已存在") from e
        return self._to_response(seasoning)

    def delete_seasoning(self, seasoning_id: str) -> bool:
        """删除调料（软删除），若仍被菜谱使用则拒绝删除"""
        if not self.repository.get_by_id(seasoning_id):
            return False
        recipes = self.repository.find_recipes_by_seasoning(seasoning_id)
        if recipes:
            titles = "、".join(title for _, title in recipes)
            raise ValueError(
                f"该调料已被 {len(recipes)} 个菜谱使用（{titles}），请先修改或删除这些菜谱后再试"
            )
        return self.repository.soft_delete(seasoning_id)

    def _to_response(self, seasoning: Seasoning) -> SeasoningResponse:
        return SeasoningResponse(
            id=seasoning.id,
            canonical_name=seasoning.canonical_name,
            pinyin=seasoning.pinyin,
            category_id=seasoning.category_id,
            category_name=self.repository.get_category_name(seasoning.category_id),
            created_at=seasoning.created_at,
            updated_at=seasoning.updated_at,
        )
