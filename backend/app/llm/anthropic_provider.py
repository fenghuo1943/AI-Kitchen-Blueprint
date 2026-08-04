"""Anthropic 云端 LLM 客户端（可选供应商）。

docs/07-LLM规范：商业 API 仅用于用户明确启用的菜谱整理/审核辅助，默认本地。
使用官方 anthropic SDK；结构化输出走 output_config.format(json_schema)，
schema 需经 sanitize_schema_for_anthropic 剥掉不支持的约束。
"""
import json
from typing import List, Optional, Type

import anthropic
from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import LLMProvider, LLMUnavailableError, LLMValidationError
from app.llm.schema import sanitize_schema_for_anthropic


class AnthropicLLMProvider(LLMProvider):
    """Anthropic 云端生成客户端。api_key 未配置时走 ANTHROPIC_API_KEY 环境变量。"""

    def __init__(
        self,
        api_key: Optional[str] = settings.LLM_API_KEY,
        model: str = settings.ANTHROPIC_LLM_MODEL,
        max_tokens: int = settings.LLM_MAX_TOKENS,
        timeout: Optional[float] = settings.LLM_TIMEOUT,
    ):
        self._client = anthropic.Anthropic(api_key=api_key or None, timeout=timeout)
        self.model = model
        self.max_tokens = max_tokens

    def generate(
        self,
        messages: List[dict],
        response_schema: Optional[Type[BaseModel]] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        client = self._client.with_options(timeout=timeout) if timeout is not None else self._client
        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if response_schema is not None:
            kwargs["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": sanitize_schema_for_anthropic(response_schema.model_json_schema()),
                }
            }

        try:
            resp = client.messages.create(**kwargs)
            text = next(b.text for b in resp.content if b.type == "text")
        except anthropic.APIConnectionError as e:
            raise LLMUnavailableError(f"Anthropic 网络错误: {e}") from e
        except anthropic.RateLimitError as e:
            raise LLMUnavailableError(f"Anthropic 限流: {e}") from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                raise LLMUnavailableError(f"Anthropic 服务错误: {e}") from e
            raise LLMValidationError(f"Anthropic 请求被拒: {e}") from e

        return self._parse(text, response_schema)

    def _parse(self, text: str, response_schema: Optional[Type[BaseModel]]) -> dict:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMValidationError(f"Anthropic 输出非合法 JSON: {e}") from e
        if response_schema is None:
            return data
        try:
            return response_schema.model_validate(data).model_dump()
        except Exception as e:  # noqa: BLE001 - Pydantic 校验错误统一包装
            raise LLMValidationError(f"Anthropic 输出未通过校验: {e}") from e

    def health_check(self) -> dict:
        try:
            self._client.models.retrieve(self.model)
            return {"ok": True, "model_available": True, "detail": "Anthropic 就绪"}
        except Exception as e:  # noqa: BLE001 - 健康检查吞掉异常
            return {"ok": False, "model_available": False, "detail": f"Anthropic 不可达: {e}"}
