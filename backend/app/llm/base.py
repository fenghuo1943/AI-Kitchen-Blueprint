"""统一 LLM Provider 抽象（docs/07-LLM规范）。

业务层仅依赖本抽象；默认本地 Ollama，可选 Anthropic 云端。
结构化输出由各实现负责强制 JSON，并在本层用 Pydantic 校验。
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Type

from pydantic import BaseModel


class LLMUnavailableError(Exception):
    """LLM 服务不可达 / 模型不可用（镜像 EmbeddingUnavailableError 的降级风格）。"""


class LLMValidationError(Exception):
    """LLM 输出未通过 JSON/Pydantic 校验（可带错误提示一次修复重试）。"""


class LLMProvider(ABC):
    """统一 LLM 生成客户端接口。"""

    @abstractmethod
    def generate(
        self,
        messages: List[dict],
        response_schema: Optional[Type[BaseModel]] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        """生成并按 response_schema 校验后返回 dict。

        messages: [{"role": "system"|"user", "content": str}, ...]
        """

    @abstractmethod
    def health_check(self) -> dict:
        """服务可用性检查，返回 {"ok": bool, "model_available": bool, "detail": str}。"""
