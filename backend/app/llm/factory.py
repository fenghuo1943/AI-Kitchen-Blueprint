"""LLM Provider 工厂（按 config 路由）。

默认本地 Ollama；LLM_PROVIDER="anthropic" 时使用 Anthropic 云端。
"""
from app.core.config import settings
from app.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    """按配置返回 LLM Provider 实例。"""
    if settings.LLM_PROVIDER == "anthropic":
        from app.llm.anthropic_provider import AnthropicLLMProvider

        return AnthropicLLMProvider()
    from app.llm.ollama import OllamaLLMProvider

    return OllamaLLMProvider()
