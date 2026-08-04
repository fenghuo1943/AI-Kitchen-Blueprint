"""RAG 索引编排：单菜索引 / 删除、全量重建。

后台线程调用本模块；每个方法自带独立 DB session（绝不复用请求期 session，
因为请求结束时 session 已关闭）。异常一律捕获为 IndexResult.error，绝不向外抛。
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.db.database import get_db_context
from app.rag.chunking import chunk_recipe, needs_reindex
from app.rag.embedding import EmbeddingUnavailableError, OllamaEmbeddingClient
from app.rag.vector_store import ChromaStore
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.recipe_repository import RecipeRepository

logger = logging.getLogger(__name__)


@dataclass
class IndexResult:
    """单道菜索引结果（后台任务返回，不对外传播异常）"""
    recipe_id: str
    action: str            # indexed | skipped | removed
    chunks_indexed: int    # 0 for removed/skipped
    error: Optional[str] = None


class RecipeIndexer:
    """索引器。构造轻量，Chroma/Ollama 均惰性初始化，Ollama 不在线不影响构造。"""

    def __init__(self, store: Optional[ChromaStore] = None,
                 embedding: Optional[OllamaEmbeddingClient] = None):
        self.store = store or ChromaStore()
        self.embedding = embedding or OllamaEmbeddingClient()

    def index_recipe(self, recipe_id: str) -> IndexResult:
        """幂等索引单道菜。

        流程：装配全量数据 → 幂等判定 → 切块 → 嵌入 → 写 Chroma → 回写 document_chunks。
        """
        try:
            with get_db_context() as db:
                data = RecipeRepository(db).get_full_for_index(recipe_id)
                # 不存在 / 非发布 / 已软删 → 清理索引（收敛到 removed 状态）
                if not data or data.get("status") != "published" or data.get("deleted_at") is not None:
                    return self.delete_index(recipe_id)

                doc_repo = DocumentChunkRepository(db)
                stored = doc_repo.get_chunks_for_recipe(recipe_id)
                if not needs_reindex(data, stored):
                    return IndexResult(recipe_id=recipe_id, action="skipped", chunks_indexed=0)

                chunks = chunk_recipe(data)
                if not chunks:
                    return IndexResult(recipe_id=recipe_id, action="skipped", chunks_indexed=0)

                vectors = self.embedding.embed_texts([c.text for c in chunks])
                n = self.store.upsert_recipe(recipe_id, data["revision"], chunks, vectors)
                if n != len(chunks):
                    raise RuntimeError(f"写入 Chroma 数量不符：{n} != {len(chunks)}")

                doc_repo.replace_for_recipe(
                    recipe_id,
                    data["revision"],
                    chunks,
                    vector_ids=[f"{c.recipe_id}:{c.chunk_type}:{c.order}" for c in chunks],
                )
                return IndexResult(recipe_id=recipe_id, action="indexed", chunks_indexed=n)
        except EmbeddingUnavailableError as e:
            logger.warning("嵌入服务不可用，菜谱 %s 暂未索引：%s", recipe_id, e)
            return IndexResult(recipe_id=recipe_id, action="skipped", chunks_indexed=0, error=str(e))
        except Exception as e:  # noqa: BLE001 - 后台任务不向外抛
            logger.exception("索引菜谱 %s 失败", recipe_id)
            return IndexResult(recipe_id=recipe_id, action="skipped", chunks_indexed=0, error=str(e))

    def delete_index(self, recipe_id: str) -> IndexResult:
        """清除单道菜的 Chroma 向量与 document_chunks 映射。"""
        try:
            self.store.delete_recipe(recipe_id)
            with get_db_context() as db:
                DocumentChunkRepository(db).delete_for_recipe(recipe_id)
            return IndexResult(recipe_id=recipe_id, action="removed", chunks_indexed=0)
        except Exception as e:  # noqa: BLE001
            logger.exception("删除菜谱 %s 索引失败", recipe_id)
            return IndexResult(recipe_id=recipe_id, action="removed", chunks_indexed=0, error=str(e))

    def rebuild_all(self) -> Dict[str, int]:
        """全量重建：索引所有 published 且未删除的菜谱，返回统计。"""
        with get_db_context() as db:
            ids = RecipeRepository(db).list_published_ids()
        stats = {"total": len(ids), "indexed": 0, "skipped": 0, "removed": 0, "failed": 0}
        for rid in ids:
            result = self.index_recipe(rid)
            if result.error:
                stats["failed"] += 1
            elif result.action == "indexed":
                stats["indexed"] += 1
            elif result.action == "removed":
                stats["removed"] += 1
            else:
                stats["skipped"] += 1
        return stats
