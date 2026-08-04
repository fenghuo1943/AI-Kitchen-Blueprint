"""统一 LLM Provider（docs/07-LLM规范：默认本地，可选商业 API）。"""
from app.llm.base import LLMProvider, LLMUnavailableError, LLMValidationError
from app.llm.factory import get_llm_provider

__all__ = ["LLMProvider", "LLMUnavailableError", "LLMValidationError", "get_llm_provider"]
