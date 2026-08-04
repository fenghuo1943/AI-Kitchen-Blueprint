"""Ollama 嵌入客户端单元测试（httpx.MockTransport 拦截，不连真实 Ollama）"""
import json

import httpx
import pytest

from app.rag.embedding import EmbeddingUnavailableError, OllamaEmbeddingClient


def _client_with(handler):
    client = OllamaEmbeddingClient(base_url="http://test")
    client._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    return client


def _req_json(request):
    return json.loads(request.content)


def test_embed_batch_calls_api_embed():
    def handler(request):
        assert request.url.path == "/api/embed"
        body = _req_json(request)
        assert body["model"] == "bge-m3"
        assert body["input"] == ["你好", "世界"]
        return httpx.Response(200, json={"embeddings": [[0.1] * 4, [0.2] * 4]})

    client = _client_with(handler)
    result = client.embed_texts(["你好", "世界"])
    assert len(result) == 2
    assert result[0] == [0.1] * 4


def test_embed_fallback_legacy_on_404():
    def handler(request):
        if request.url.path == "/api/embed":
            return httpx.Response(404, text="not found")
        assert request.url.path == "/api/embeddings"
        return httpx.Response(200, json={"embedding": [0.3] * 4})

    client = _client_with(handler)
    assert client.embed_text("测试") == [0.3] * 4


def test_network_error_raises():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    client = _client_with(handler)
    with pytest.raises(EmbeddingUnavailableError):
        client.embed_text("测试")


def test_health_check_model_available():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "bge-m3:latest"}, {"name": "qwen2.5"}]})

    client = _client_with(handler)
    health = client.health_check()
    assert health["ok"] is True
    assert health["model_available"] is True


def test_health_check_model_missing():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "qwen2.5"}]})

    client = _client_with(handler)
    health = client.health_check()
    assert health["ok"] is True
    assert health["model_available"] is False
    assert "bge-m3" in health["detail"]


def test_health_check_ollama_down():
    def handler(request):
        raise httpx.ConnectError("refused")

    client = _client_with(handler)
    health = client.health_check()
    assert health["ok"] is False
    assert health["model_available"] is False
