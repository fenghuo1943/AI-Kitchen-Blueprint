"""RAG 冒烟测试脚本：Ollama 健康检查 → 全量重建索引 → 索引状态 → 语义检索。

运行方式（在 backend 目录下）：
    ../venv/Scripts/python.exe scripts/rag_smoke_test.py
前置：
    ollama serve
    ollama pull bge-m3
"""
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台 UTF-8 输出

# 添加 backend 目录到 Python 路径（与 scripts/init_seed_data.py 一致）
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings  # noqa: E402
from app.rag.embedding import OllamaEmbeddingClient  # noqa: E402
from app.rag.indexer import RecipeIndexer  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402
from app.rag.vector_store import ChromaStore  # noqa: E402
from app.db.database import get_db_context  # noqa: E402
from app.repositories.document_chunk_repository import DocumentChunkRepository  # noqa: E402
from app.repositories.recipe_repository import RecipeRepository  # noqa: E402


def section(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    print(f"EMBEDDING_BASE_URL = {settings.EMBEDDING_BASE_URL}")
    print(f"EMBEDDING_MODEL    = {settings.EMBEDDING_MODEL}")
    print(f"VECTOR_STORE_PATH  = {settings.VECTOR_STORE_PATH}")

    # 1) Ollama / bge-m3 健康检查
    section("1. Ollama / bge-m3 健康检查")
    embedding = OllamaEmbeddingClient()
    health = embedding.health_check()
    print(health)
    if not (health.get("ok") and health.get("model_available")):
        print("嵌入服务不可用，终止测试。请先 ollama serve 并 ollama pull bge-m3。")
        return

    sample = embedding.embed_text("番茄炒鸡蛋")
    print(f"示例嵌入：dim={len(sample)}")

    # 2) 全量重建索引
    section("2. 全量重建索引（所有 published 菜谱）")
    indexer = RecipeIndexer()
    t0 = time.time()
    stats = indexer.rebuild_all()
    print(f"统计: {stats}")
    print(f"重建耗时: {time.time() - t0:.1f}s")
    store = ChromaStore()
    print(f"Chroma 块总数: {store.count()}")

    # 3) 索引状态
    section("3. 索引状态")
    with get_db_context() as db:
        doc_repo = DocumentChunkRepository(db)
        recipe_repo = RecipeRepository(db)
        indexed = len(doc_repo.indexed_recipe_ids())
        published = len(recipe_repo.list_published_ids())
        by_type = doc_repo.count_by_type()
        print(f"已索引菜谱: {indexed} / 已发布菜谱: {published}")
        print(f"各类型块数: {by_type}")

    # 4) 语义检索示例
    section("4. 语义检索示例")
    queries = ["番茄炒鸡蛋怎么做", "晚上想吃点热乎的汤", "红烧肉"]
    retriever = HybridRetriever()
    with get_db_context() as db:
        for q in queries:
            print(f"\n查询: 「{q}」")
            result = retriever.retrieve(db, q, rerank_top_k=5)
            if not result.engine_available:
                print(f"  检索引擎不可用: {result.error}")
                continue
            if not result.hits:
                print("  无命中")
                continue
            for i, hit in enumerate(result.hits, 1):
                chunk_types = "、".join(sorted({c["chunk_type"] for c in hit.chunks}))
                print(f"  {i}. [{hit.score:.3f}] {hit.title}  (命中块: {chunk_types})")
                if hit.matched_ingredients:
                    print(f"     食材匹配: {'、'.join(hit.matched_ingredients)}")


if __name__ == "__main__":
    main()
