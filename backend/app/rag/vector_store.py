"""Chroma 持久化向量库封装。

Chroma 仅保存检索映射（非权威数据源）；关系库是权威数据源，向量库可随时全量重建。
"""
import sys
from typing import List, Optional

# Windows sqlite 兼容 shim：chromadb 要求 sqlite3 >= 3.35，
# 若解释器自带 sqlite 过旧，用 pysqlite3-binary 替换。
try:
    import pysqlite3  # type: ignore
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import chromadb  # noqa: E402

from app.core.config import settings
from app.rag.chunking import Chunk


class ChromaStore:
    """Chroma collection 封装。

    collection 元数据（每文档 5 键）：recipe_id / revision / chunk_type / content_hash / source_url
    文档 ID：f"{recipe_id}:{chunk_type}:{order}"
    注意：持久化路径相对进程 CWD，部署时建议改为绝对路径。
    """

    def __init__(self, path: Optional[str] = None, collection_name: Optional[str] = None):
        self._path = path or settings.VECTOR_STORE_PATH
        self._collection_name = collection_name or settings.CHROMA_COLLECTION
        self._client = None
        self._collection = None

    def _ensure(self):
        """惰性初始化客户端与 collection（首个调用才创建）。"""
        if self._collection is None:
            self._client = chromadb.PersistentClient(
                path=self._path,
                settings=chromadb.Settings(anonymized_telemetry=False, allow_reset=True),
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": settings.CHROMA_SPACE},
            )

    def upsert_recipe(self, recipe_id: str, revision: int,
                      chunks: List[Chunk], vectors: List[List[float]]) -> int:
        """写入一道菜的切块向量（先删旧再整体写，保证幂等）。返回写入条数。"""
        self._ensure()
        self.delete_recipe(recipe_id)
        if not chunks or not vectors or len(chunks) != len(vectors):
            return 0
        ids = [f"{c.recipe_id}:{c.chunk_type}:{c.order}" for c in chunks]
        metadatas = [
            {
                "recipe_id": c.recipe_id,
                "revision": c.revision,
                "chunk_type": c.chunk_type,
                "content_hash": c.content_hash,
                "source_url": c.source_url or "",
            }
            for c in chunks
        ]
        self._collection.upsert(
            ids=ids,
            documents=[c.text for c in chunks],
            embeddings=vectors,
            metadatas=metadatas,
        )
        return len(chunks)

    def delete_recipe(self, recipe_id: str) -> None:
        """按 recipe_id 删除整道菜的向量。"""
        self._ensure()
        self._collection.delete(where={"recipe_id": recipe_id})

    def query(self, text_embedding: List[float], top_k: int,
              where: Optional[dict] = None) -> List[dict]:
        """向量召回，返回命中块列表（按相似度降序）。"""
        self._ensure()
        if top_k <= 0:
            return []
        kwargs = {
            "query_embeddings": [text_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where is not None:
            kwargs["where"] = where
        res = self._collection.query(**kwargs)
        hits = []
        for i, doc_id in enumerate((res.get("ids") or [[]])[0]):
            meta = (res.get("metadatas") or [[]])[0][i] or {}
            distance = (res.get("distances") or [[]])[0][i]
            hits.append({
                "id": doc_id,
                "recipe_id": meta.get("recipe_id", ""),
                "revision": meta.get("revision"),
                "chunk_type": meta.get("chunk_type", ""),
                "content_hash": meta.get("content_hash", ""),
                "source_url": meta.get("source_url") or None,
                "text": (res.get("documents") or [[]])[0][i],
                "vector_score": max(0.0, 1.0 - distance),  # cosine 距离 → 相似度
            })
        return hits

    def count(self) -> int:
        self._ensure()
        return self._collection.count()

    def clear(self) -> None:
        """清空整个 collection（用于重建/测试）。"""
        if self._client is not None:
            try:
                self._client.delete_collection(self._collection_name)
            except Exception:
                pass
            self._collection = None


# 模块级单例（惰性：首个调用才打开 client）
store = ChromaStore()
