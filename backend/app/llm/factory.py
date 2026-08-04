"""LLM Provider 工厂（按 config 路由，支持按任务指定供应商/模型）。

默认本地 Ollama；LLM_PROVIDER="anthropic" 时使用 Anthropic 云端；
"deepseek" / "openrouter" / "openai_compat" 时使用 OpenAI 兼容云端端点。
build_llm_provider 支持用户在前端选择具体模型（AI 采集）。
"""
from typing import Optional

from app.core.config import settings
from app.llm.base import LLMProvider


def default_model_for(provider: Optional[str]) -> str:
    """按供应商返回默认模型名；未知供应商回落本地 LLM_MODEL。"""
    provider = provider or settings.LLM_PROVIDER
    if provider == "anthropic":
        return settings.ANTHROPIC_LLM_MODEL
    if provider == "deepseek":
        return settings.DEEPSEEK_MODEL
    if provider == "openrouter":
        return settings.OPENROUTER_MODEL
    if provider == "openai_compat":
        return settings.OPENAI_COMPAT_MODEL
    return settings.LLM_MODEL


def build_llm_provider(provider: Optional[str] = None, model: Optional[str] = None) -> LLMProvider:
    """按供应商与模型名构造 Provider；缺省回落到配置。"""
    provider = provider or settings.LLM_PROVIDER
    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicLLMProvider

        return AnthropicLLMProvider(model=model or settings.ANTHROPIC_LLM_MODEL)
    if provider == "deepseek":
        from app.llm.openai_compat import OpenAICompatLLMProvider

        return OpenAICompatLLMProvider(
            api_key=settings.DEEPSEEK_API_KEY or settings.LLM_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=model or settings.DEEPSEEK_MODEL,
        )
    if provider == "openrouter":
        from app.llm.openai_compat import OpenAICompatLLMProvider

        return OpenAICompatLLMProvider(
            api_key=settings.OPENROUTER_API_KEY or settings.LLM_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model=model or settings.OPENROUTER_MODEL,
        )
    if provider == "openai_compat":
        from app.llm.openai_compat import OpenAICompatLLMProvider

        return OpenAICompatLLMProvider(
            api_key=settings.OPENAI_COMPAT_API_KEY or settings.LLM_API_KEY,
            base_url=settings.OPENAI_COMPAT_BASE_URL or settings.LLM_BASE_URL,
            model=model or settings.OPENAI_COMPAT_MODEL,
        )
    from app.llm.ollama import OllamaLLMProvider

    return OllamaLLMProvider(model=model or settings.LLM_MODEL)


def get_llm_provider() -> LLMProvider:
    """按配置返回 LLM Provider 实例。"""
    return build_llm_provider()
