"""统一 LLM Provider（docs/07-LLM规范：默认本地，可选商业 API）。"""
from app.llm.base import LLMProvider, LLMUnavailableError, LLMValidationError
from app.llm.factory import build_llm_provider, default_model_for, get_llm_provider
from app.llm.openai_compat import OpenAICompatLLMProvider

__all__ = [
    "LLMProvider", "LLMUnavailableError", "LLMValidationError",
    "build_llm_provider", "default_model_for", "get_llm_provider", "OpenAICompatLLMProvider",
]
