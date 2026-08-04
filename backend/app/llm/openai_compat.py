"""OpenAI 兼容云端 LLM 客户端（可选供应商：DeepSeek / OpenRouter / 任意兼容端点）。

docs/07-LLM规范：商业 API 仅用于用户明确启用的菜谱整理/审核辅助，默认本地。
DeepSeek、OpenRouter（含小米 MiMo）等均走 OpenAI 协议（POST /chat/completions），
本类用 httpx 直连，不引入 openai SDK；结构化输出带 response_format=json_object，
部分代理不支持时回退自由 JSON，统一 Pydantic 校验。
"""
import json
from typing import List, Optional, Type

import httpx
from pydantic import BaseModel

from app.llm.base import LLMProvider, LLMUnavailableError, LLMValidationError


class OpenAICompatLLMProvider(LLMProvider):
    """OpenAI 兼容 chat completions 客户端。

    base_url 需指向 OpenAI 兼容端点根（如 https://api.deepseek.com、
    https://openrouter.ai/api/v1），请求走 /chat/completions、/models。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "",
        max_tokens: int = 4000,
        timeout: float = 120.0,
        temperature: float = 0.2,
    ):
        from app.core.config import settings

        self._client = httpx.Client(base_url=base_url or "", timeout=timeout)
        self.model = model or settings.LLM_MODEL
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def generate(
        self,
        messages: List[dict],
        response_schema: Optional[Type[BaseModel]] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        # 有 schema 时请求 json_object 模式；部分代理不支持（400）则去掉重试
        if response_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = self._client.post(
                "/chat/completions", json=payload, headers=self._headers, timeout=timeout
            )
            if resp.status_code == 400 and payload.get("response_format"):
                # 旧版/受限代理不接受 response_format，回退自由 JSON
                payload.pop("response_format", None)
                resp = self._client.post(
                    "/chat/completions", json=payload, headers=self._headers, timeout=timeout
                )
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"OpenAI 兼容服务不可达: {e}") from e

        if resp.status_code in (401, 403):
            raise LLMUnavailableError(f"OpenAI 兼容服务鉴权失败 (HTTP {resp.status_code})")
        if resp.status_code >= 500:
            detail = resp.text[:300]
            raise LLMUnavailableError(f"OpenAI 兼容服务错误 (HTTP {resp.status_code}): {detail}")
        if resp.status_code != 200:
            detail = resp.text[:300]
            raise LLMValidationError(f"OpenAI 兼容请求被拒 (HTTP {resp.status_code}): {detail}")

        try:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (ValueError, IndexError, AttributeError) as e:
            raise LLMValidationError(f"OpenAI 兼容响应结构异常: {e}") from e

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
            raise LLMValidationError(f"OpenAI 兼容输出非合法 JSON: {e}") from e
        if response_schema is None:
            return data
        try:
            return response_schema.model_validate(data).model_dump()
        except Exception as e:  # noqa: BLE001 - Pydantic 校验错误统一包装
            raise LLMValidationError(f"OpenAI 兼容输出未通过校验: {e}") from e

    def _list_ids(self) -> List[str]:
        """GET /models 返回模型 id 列表（DeepSeek/OpenRouter 均支持）。"""
        try:
            resp = self._client.get("/models", headers=self._headers)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"OpenAI 兼容服务不可达: {e}") from e
        return [
            m.get("id", "")
            for m in resp.json().get("data", [])
            if m.get("id")
        ]

    def list_models(self) -> List[str]:
        """枚举当前供应商可用的模型 id。"""
        return self._list_ids()

    def health_check(self) -> dict:
        try:
            model_ids = self._list_ids()
        except LLMUnavailableError as e:
            return {"ok": False, "model_available": False, "detail": str(e)}
        # 精确匹配或按最后一段路径匹配（openrouter 可能带 vendor 前缀）
        available = self.model in model_ids or any(
            mid.split("/")[-1] == self.model.split("/")[-1] for mid in model_ids
        )
        return {
            "ok": True,
            "model_available": available,
            "detail": "模型已就绪" if available else f"未找到模型 {self.model}",
        }
