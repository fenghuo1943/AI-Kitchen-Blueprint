"""Ollama 本地 LLM 客户端（默认供应商，数据不出本机）。

调用 POST /api/chat；结构化输出优先带 JSON Schema（Ollama >= 0.5 支持 format 传对象），
旧版返回 400 时回退 format="json"。
"""
import json
from typing import List, Optional, Type

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import LLMProvider, LLMUnavailableError, LLMValidationError


class OllamaLLMProvider(LLMProvider):
    """Ollama 本地生成客户端。"""

    def __init__(
        self,
        base_url: str = settings.LLM_BASE_URL,
        model: str = settings.LLM_MODEL,
        timeout: int = settings.LLM_TIMEOUT,
        temperature: float = settings.LLM_TEMPERATURE,
    ):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        self.model = model
        self.temperature = temperature

    def generate(
        self,
        messages: List[dict],
        response_schema: Optional[Type[BaseModel]] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        payload: dict = {
            "model": self.model,
            "stream": False,
            "messages": messages,
            "options": {"temperature": self.temperature},
        }
        if response_schema is not None:
            payload["format"] = response_schema.model_json_schema()

        try:
            resp = self._client.post("/api/chat", json=payload, timeout=timeout)
            if resp.status_code == 400 and isinstance(payload.get("format"), dict):
                # 旧版 Ollama 不接受 schema 对象，回退自由 JSON
                payload["format"] = "json"
                resp = self._client.post("/api/chat", json=payload, timeout=timeout)
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"Ollama 不可达: {e}") from e

        return self._parse(content, response_schema)

    def _parse(self, content: str, response_schema: Optional[Type[BaseModel]]) -> dict:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMValidationError(f"Ollama 输出非合法 JSON: {e}") from e
        if response_schema is None:
            return data
        try:
            return response_schema.model_validate(data).model_dump()
        except Exception as e:  # noqa: BLE001 - Pydantic 校验错误统一包装
            raise LLMValidationError(f"Ollama 输出未通过校验: {e}") from e

    def list_models(self) -> list[str]:
        """列出 Ollama 已拉取且支持文本生成（completion）的模型名。"""
        try:
            resp = self._client.get("/api/tags")
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"Ollama 不可达: {e}") from e
        names = []
        for m in resp.json().get("models", []):
            caps = m.get("capabilities") or []
            name = m.get("name", "")
            if "completion" in caps and name:
                names.append(name)
        return names

    def health_check(self) -> dict:
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
                "detail": "模型已就绪" if available else f"未找到模型 {self.model}，请先 ollama pull {self.model}",
            }
        except httpx.HTTPError as e:
            return {"ok": False, "model_available": False, "detail": f"Ollama 不可达: {e}"}
