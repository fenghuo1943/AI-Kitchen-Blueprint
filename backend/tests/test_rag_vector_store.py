"""Chroma 向量库单元测试（临时目录隔离）"""
import hashlib

from app.rag.chunking import Chunk


def _chunks(recipe_id="r1", revision=1, texts=None):
    texts = texts or ["番茄炒蛋做法", "先把鸡蛋打散"]
    chunks = []
    for i, text in enumerate(texts):
        chunks.append(Chunk(
            recipe_id=recipe_id,
            revision=revision,
            chunk_type="overview" if i == 0 else "ingredients",
            text=text,
            content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            source_url=None,
            order=i,
        ))
    return chunks


def _vec(seed=0.1):
    return [seed] * 16


def test_upsert_query_delete(rag_store):
    chunks = _chunks(texts=["番茄炒蛋怎么做", "先把鸡蛋打散"])
    vectors = [_vec(), _vec(seed=0.2)]
    n = rag_store.upsert_recipe("r1", 1, chunks, vectors)
    assert n == 2
    assert rag_store.count() == 2

    hits = rag_store.query(_vec(), top_k=2)
    assert len(hits) == 2
    assert {h["recipe_id"] for h in hits} == {"r1"}
    assert all(h["chunk_type"] in ("overview", "ingredients") for h in hits)
    assert all("vector_score" in h for h in hits)

    rag_store.delete_recipe("r1")
    assert rag_store.count() == 0


def test_upsert_replaces_previous_revision(rag_store):
    rag_store.upsert_recipe("r1", 1, _chunks(texts=["第一版"]), [_vec()])
    assert rag_store.count() == 1

    chunks2 = _chunks(texts=["第二版", "第二版食材"])
    rag_store.upsert_recipe("r1", 2, chunks2, [_vec(), _vec(seed=0.2)])
    assert rag_store.count() == 2
    texts = {h["text"] for h in rag_store.query(_vec(), top_k=5)}
    assert texts == {"第二版", "第二版食材"}


def test_query_where_filter(rag_store):
    rag_store.upsert_recipe("r1", 1, _chunks(recipe_id="r1", texts=["a"]), [_vec()])
    rag_store.upsert_recipe("r2", 1, _chunks(recipe_id="r2", texts=["b"]), [_vec(seed=0.3)])

    hits = rag_store.query(_vec(), top_k=5, where={"recipe_id": {"$in": ["r1"]}})
    assert {h["recipe_id"] for h in hits} == {"r1"}


def test_count_empty_store(rag_store):
    assert rag_store.count() == 0
    assert rag_store.query(_vec(), top_k=5) == []
