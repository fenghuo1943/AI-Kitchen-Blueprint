"""Ollama 嵌入客户端（bge-m3 本地嵌入，数据不出本机）。

调用现代端点 POST /api/embed（批量）；兼容旧版 POST /api/embeddings（单条）。
"""
from typing import List

import httpx

from app.core.config import settings


class EmbeddingUnavailableError(Exception):
    """Ollama 不可达 / 嵌入模型未拉取的类型化错误，由 indexer / retriever 捕获降级。"""


class OllamaEmbeddingClient:
    """Ollama 本地嵌入客户端。"""

    def __init__(
        self,
        base_url: str = settings.EMBEDDING_BASE_URL,
        model: str = settings.EMBEDDING_MODEL,
        batch_size: int = settings.EMBEDDING_BATCH_SIZE,
        timeout: int = settings.EMBEDDING_TIMEOUT,
    ):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        self.model = model
        self.batch_size = batch_size

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """分批嵌入文本。任一失败抛 EmbeddingUnavailableError。"""
        if not texts:
            return []
        results: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            results.extend(self._embed_batch(texts[i:i + self.batch_size]))
        return results

    def embed_text(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    def _embed_batch(self, batch: List[str]) -> List[List[float]]:
        try:
            resp = self._client.post("/api/embed", json={"model": self.model, "input": batch})
            if resp.status_code == 404:
                # 旧版 Ollama 无 /api/embed，回退单条端点
                return [self._embed_legacy(t) for t in batch]
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings") or []
            if len(embeddings) != len(batch):
                raise EmbeddingUnavailableError(
                    f"Ollama 返回嵌入数量({len(embeddings)})与输入({len(batch)})不一致"
                )
            return embeddings
        except EmbeddingUnavailableError:
            raise
        except httpx.HTTPError as e:
            raise EmbeddingUnavailableError(f"Ollama 嵌入服务不可达: {e}") from e
        except Exception as e:
            raise EmbeddingUnavailableError(f"Ollama 嵌入失败: {e}") from e

    def _embed_legacy(self, text: str) -> List[float]:
        try:
            resp = self._client.post("/api/embeddings", json={"model": self.model, "prompt": text})
            resp.raise_for_status()
            return resp.json()["embedding"]
        except httpx.HTTPError as e:
            raise EmbeddingUnavailableError(f"Ollama 旧版嵌入接口不可达: {e}") from e

    def health_check(self) -> dict:
        """检查 Ollama 是否在线、嵌入模型是否已拉取。"""
        try:
            resp = self._client.get("/api/tags")
            resp.raise_for_status()
            model_names = [m.get("name", "") for m in resp.json().get("models", [])]
            available = any(
                self.model == name or name.split(":")[0] == self.model
                for name in model_names
            )
            return {
                "ok": True,
                "model_available": available,
                "detail": "模型已就绪" if available else f"未找到嵌入模型 {self.model}，请先执行 ollama pull {self.model}",
            }
        except httpx.HTTPError as e:
            return {"ok": False, "model_available": False, "detail": f"Ollama 不可达: {e}"}
