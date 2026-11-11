from typing import Optional

from app.adapters.base_adapter import (
    CircuitBreaker,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMStreamChunk,
)
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.core.config import settings
from app.core.exceptions import LLMConfigurationError

_circuit_breakers: dict[str, CircuitBreaker] = {}


def _get_circuit_breaker(provider_name: str) -> CircuitBreaker:
    if provider_name not in _circuit_breakers:
        _circuit_breakers[provider_name] = CircuitBreaker(
            failure_threshold=settings.CIRCUIT_BREAKER_THRESHOLD,
            reset_timeout=settings.CIRCUIT_BREAKER_RESET_SECONDS,
        )
    return _circuit_breakers[provider_name]


def reset_circuit_breakers() -> None:
    """Đặt lại toàn bộ Circuit Breaker (hữu ích cho kiểm thử)."""
    _circuit_breakers.clear()


def get_llm_adapter(provider: Optional[str] = None) -> LLMProvider:
    """Factory khởi tạo LLM Adapter dựa trên cấu hình LLM_PROVIDER."""
    selected = (provider or settings.LLM_PROVIDER or "gemini").strip().lower()
    breaker = _get_circuit_breaker(selected)

    if selected == "gemini":
        return GeminiAdapter(circuit_breaker=breaker)
    if selected == "openai":
        return OpenAIAdapter(circuit_breaker=breaker)

    raise LLMConfigurationError(f"Unsupported LLM_PROVIDER: '{selected}'")


__all__ = [
    "CircuitBreaker",
    "LLMMessage",
    "LLMProvider",
    "LLMResponse",
    "LLMStreamChunk",
    "GeminiAdapter",
    "OpenAIAdapter",
    "get_llm_adapter",
    "reset_circuit_breakers",
]
