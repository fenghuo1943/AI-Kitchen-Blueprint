"""document_chunks（RAG 索引映射）数据访问层。

关系库是权威数据源；本表保存"哪道菜的哪些块已入向量库"的映射与 content_hash，
用于幂等判定与索引状态统计。向量本体在 Chroma 中，此处仅存 vector_id 引用。
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.rag.chunking import Chunk


class DocumentChunkRepository:
    """document_chunks 表读写。"""

    def __init__(self, db: Session):
        self.db = db

    def get_chunks_for_recipe(self, recipe_id: str) -> List[Tuple[int, str]]:
        """读取某道菜已入库块的 (revision, content_hash)。"""
        rows = self.db.query(DocumentChunk.revision, DocumentChunk.content_hash).filter(
            DocumentChunk.recipe_id == recipe_id
        ).all()
        return [(r, h) for r, h in rows]

    def replace_for_recipe(self, recipe_id: str, revision: int,
                           chunks: List[Chunk], vector_ids: List[str]) -> None:
        """先删后插，整体替换某道菜的映射（幂等）。"""
        self.delete_for_recipe(recipe_id)
        now = datetime.utcnow()
        for chunk, vector_id in zip(chunks, vector_ids):
            self.db.add(DocumentChunk(
                id=str(uuid.uuid4()),
                recipe_id=chunk.recipe_id,
                revision=revision,
                chunk_type=chunk.chunk_type,
                content_hash=chunk.content_hash,
                vector_id=vector_id,
                source_url=chunk.source_url,
                created_at=now,
            ))
        self.db.commit()

    def delete_for_recipe(self, recipe_id: str) -> None:
        """删除某道菜的全部映射。"""
        self.db.query(DocumentChunk).filter(DocumentChunk.recipe_id == recipe_id).delete()
        self.db.commit()

    def indexed_recipe_ids(self) -> Set[str]:
        """已入向量库的去重菜谱 ID 集合。"""
        rows = self.db.query(DocumentChunk.recipe_id).distinct().all()
        return {r[0] for r in rows}

    def count_by_type(self) -> Dict[str, int]:
        """各切块类型的块数量统计。"""
        rows = self.db.query(DocumentChunk.chunk_type, func.count(DocumentChunk.id)).group_by(
            DocumentChunk.chunk_type
        ).all()
        return {t: c for t, c in rows}

    def max_revision(self, recipe_id: str) -> Optional[int]:
        row = self.db.query(func.max(DocumentChunk.revision)).filter(
            DocumentChunk.recipe_id == recipe_id
        ).scalar()
        return row
