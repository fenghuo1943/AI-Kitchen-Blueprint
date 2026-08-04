"""RAG API 集成测试（临时 Chroma + 伪嵌入器 + 后台任务同步模式）"""
from app.rag.embedding import EmbeddingUnavailableError
from tests.rag_helpers import make_recipe


def test_search_returns_hits(client, db_session, rag_engine, sync_tasks):
    recipe = make_recipe(db_session, title="番茄炒鸡蛋")
    # 入索引（后台任务同步执行）
    resp = client.post(f"/api/v1/rag/index/{recipe.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    data = client.post("/api/v1/rag/search", json={"query": "番茄炒鸡蛋怎么做"}).json()
    assert data["engine_available"] is True
    assert data["total"] >= 1
    assert any(item["recipe_id"] == recipe.id for item in data["results"])
    assert data["results"][0]["score"] > 0
    assert data["results"][0]["chunks"]  # 命中块原文，供后续 LLM 消费


def test_search_degraded_when_embedding_down(client, db_session, rag_engine, sync_tasks, monkeypatch):
    make_recipe(db_session)  # 有候选才进入嵌入步骤

    class Boom:
        def embed_text(self, text):
            raise EmbeddingUnavailableError("Ollama 不可达")

    # 覆盖 retriever 默认嵌入实现 → 触发降级
    monkeypatch.setattr("app.rag.retriever.OllamaEmbeddingClient", Boom)

    resp = client.post("/api/v1/rag/search", json={"query": "随便什么菜"})
    assert resp.status_code == 200  # 不 503，降级返回
    data = resp.json()
    assert data["engine_available"] is False
    assert data["error"]


def test_index_status_counts(client, db_session, rag_engine, sync_tasks):
    recipe = make_recipe(db_session)
    client.post(f"/api/v1/rag/index/{recipe.id}")

    data = client.get("/api/v1/rag/index/status").json()
    assert data["published_count"] == 1
    assert data["indexed_count"] == 1
    assert data["breakdown_by_type"]["overview"] >= 1
    assert data["breakdown_by_type"]["ingredients"] >= 1


def test_rebuild_single_flight(client, db_session, rag_engine, sync_tasks):
    make_recipe(db_session)
    resp = client.post("/api/v1/rag/index/rebuild")
    assert resp.status_code == 200
    assert resp.json()["task"] == "rebuild"

    data = client.get("/api/v1/rag/index/status").json()
    assert data["indexed_count"] == 1


def test_search_empty_when_no_candidates(client, db_session, rag_engine, sync_tasks):
    data = client.post("/api/v1/rag/search", json={"query": "番茄炒鸡蛋"}).json()
    assert data["total"] == 0
    assert data["engine_available"] is True
