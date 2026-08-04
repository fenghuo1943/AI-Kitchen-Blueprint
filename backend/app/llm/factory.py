"""LLM Provider 工厂（按 config 路由，支持按任务指定供应商/模型）。

默认本地 Ollama；LLM_PROVIDER="anthropic" 时使用 Anthropic 云端。
build_llm_provider 支持用户在前端选择具体模型（AI 采集）。
"""
from typing import Optional

from app.core.config import settings
from app.llm.base import LLMProvider


def build_llm_provider(provider: Optional[str] = None, model: Optional[str] = None) -> LLMProvider:
    """按供应商与模型名构造 Provider；缺省回落到配置。"""
    provider = provider or settings.LLM_PROVIDER
    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicLLMProvider

        return AnthropicLLMProvider(model=model or settings.ANTHROPIC_LLM_MODEL)
    from app.llm.ollama import OllamaLLMProvider

    return OllamaLLMProvider(model=model or settings.LLM_MODEL)


def get_llm_provider() -> LLMProvider:
    """按配置返回 LLM Provider 实例。"""
    return build_llm_provider()
