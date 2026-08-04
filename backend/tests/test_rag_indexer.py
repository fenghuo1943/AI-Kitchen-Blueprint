"""RAG 索引器集成测试（临时 Chroma + 伪嵌入器 + SQLite 内存库）"""
from app.rag.embedding import EmbeddingUnavailableError
from app.rag.indexer import RecipeIndexer
from tests.rag_helpers import make_recipe


def test_index_recipe_idempotent(db_session, rag_engine):
    recipe = make_recipe(db_session)
    indexer = RecipeIndexer()

    r1 = indexer.index_recipe(recipe.id)
    assert r1.action == "indexed"
    assert r1.chunks_indexed > 0

    r2 = indexer.index_recipe(recipe.id)
    assert r2.action == "skipped"

    assert indexer.store.count() == r1.chunks_indexed


def test_index_after_content_change_reindexes(db_session, rag_engine):
    recipe = make_recipe(db_session, title="番茄炒鸡蛋")
    indexer = RecipeIndexer()
    assert indexer.index_recipe(recipe.id).action == "indexed"

    # 内容变化但 revision 不变 → 应重新索引
    recipe.title = "西红柿炒蛋"
    db_session.commit()
    assert indexer.index_recipe(recipe.id).action == "indexed"


def test_delete_index_removes_everything(db_session, rag_engine):
    recipe = make_recipe(db_session)
    indexer = RecipeIndexer()
    indexer.index_recipe(recipe.id)
    assert indexer.store.count() > 0

    result = indexer.delete_index(recipe.id)
    assert result.action == "removed"
    assert indexer.store.count() == 0


def test_index_non_published_returns_removed(db_session, rag_engine):
    recipe = make_recipe(db_session, status="draft")
    indexer = RecipeIndexer()
    result = indexer.index_recipe(recipe.id)
    assert result.action == "removed"
    assert indexer.store.count() == 0


def test_embedding_error_recorded_not_raised(db_session, rag_engine, monkeypatch):
    recipe = make_recipe(db_session)
    indexer = RecipeIndexer()

    class Boom:
        def embed_texts(self, texts):
            raise EmbeddingUnavailableError("Ollama 挂了")

    monkeypatch.setattr(indexer, "embedding", Boom())
    result = indexer.index_recipe(recipe.id)
    assert result.error is not None
    assert "Ollama" in result.error


def test_rebuild_all_indexes_published(db_session, rag_engine):
    make_recipe(db_session)  # published
    make_recipe(db_session, title="红烧肉", status="draft", ingredient_name="猪肉")  # draft 不索引

    indexer = RecipeIndexer()
    stats = indexer.rebuild_all()
    assert stats["total"] == 1
    assert stats["indexed"] == 1
    assert stats["failed"] == 0
    assert indexer.store.count() > 0
