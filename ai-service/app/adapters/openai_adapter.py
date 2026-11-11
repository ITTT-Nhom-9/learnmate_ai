import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import (
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.adapters.base_adapter import (
    CircuitBreaker,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMStreamChunk,
)
from app.core.config import settings
from app.core.exceptions import (
    AIException,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    mask_sensitive_text,
)

logger = logging.getLogger("ai-service.openai")


class OpenAIAdapter(LLMProvider):
    """Adapter dự phòng kết nối OpenAI Chat Completions API theo mẫu Adapter Pattern."""

    provider_name: str = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else settings.OPENAI_API_KEY) or ""
        self.model_name = (model_name or settings.LLM_MODEL or "gpt-4o-mini").strip()
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.AI_TIMEOUT_SECONDS
        )
        self.max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=settings.CIRCUIT_BREAKER_THRESHOLD,
            reset_timeout=settings.CIRCUIT_BREAKER_RESET_SECONDS,
        )

    def __repr__(self) -> str:
        return f"<OpenAIAdapter(model='{self.model_name}', configured={bool(self._api_key.strip())})>"

    def _get_client(self) -> AsyncOpenAI:
        if not self._api_key.strip():
            raise LLMConfigurationError("OPENAI_API_KEY is not configured")
        return AsyncOpenAI(api_key=self._api_key, timeout=self.timeout_seconds)

    @staticmethod
    def _build_messages(
        messages: List[LLMMessage], system_prompt: Optional[str]
    ) -> List[Dict[str, str]]:
        payload: List[Dict[str, str]] = []
        if system_prompt and system_prompt.strip():
            payload.append({"role": "system", "content": system_prompt.strip()})
        for msg in messages:
            payload.append({"role": msg.role, "content": msg.content})
        if not any(m["role"] != "system" for m in payload):
            raise AIException(
                message="At least one user or assistant message is required",
                status_code=400,
                error_code="EMPTY_MESSAGES",
            )
        return payload

    @staticmethod
    def _map_exception(exc: Exception) -> AIException:
        if isinstance(exc, AIException):
            return exc
        safe_msg = mask_sensitive_text(str(exc))
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError, APITimeoutError)):
            return LLMTimeoutError(f"OpenAI request timed out: {safe_msg}")
        if isinstance(exc, RateLimitError):
            return LLMRateLimitError(f"OpenAI API rate limit exceeded: {safe_msg}")
        if isinstance(exc, AuthenticationError):
            return LLMConfigurationError("OpenAI API authentication failed; verify OPENAI_API_KEY")
        return LLMUpstreamError(f"OpenAI API error: {safe_msg}")

    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        self.circuit_breaker.ensure_closed()
        client = self._get_client()
        payload = self._build_messages(messages, system_prompt)

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": payload,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_mime_type == "application/json":
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(self.max_retries + 1):
            start_ts = time.perf_counter()
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(**kwargs),
                    timeout=self.timeout_seconds,
                )
                latency_ms = int((time.perf_counter() - start_ts) * 1000)
                content = response.choices[0].message.content or ""
                usage = response.usage
                p_t = int(getattr(usage, "prompt_tokens", 0) or 0)
                c_t = int(getattr(usage, "completion_tokens", 0) or 0)
                t_t = int(getattr(usage, "total_tokens", 0) or (p_t + c_t))
                self.circuit_breaker.record_success()
                return LLMResponse(
                    content=content,
                    provider=self.provider_name,
                    model=self.model_name,
                    tokens_prompt=p_t,
                    tokens_completion=c_t,
                    total_tokens=t_t,
                    latency_ms=latency_ms,
                )
            except Exception as exc:
                logger.warning(
                    "OpenAI chat attempt %d/%d failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    mask_sensitive_text(str(exc)),
                )
                retryable = isinstance(
                    exc, (asyncio.TimeoutError, TimeoutError, APITimeoutError, RateLimitError, InternalServerError)
                )
                if attempt < self.max_retries and retryable:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                self.circuit_breaker.record_failure()
                raise self._map_exception(exc) from exc

        self.circuit_breaker.record_failure()
        raise LLMUpstreamError("OpenAI request failed after retries")

    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        self.circuit_breaker.ensure_closed()
        client = self._get_client()
        payload = self._build_messages(messages, system_prompt)

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": payload,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        start_ts = time.perf_counter()
        try:
            response_stream = await asyncio.wait_for(
                client.chat.completions.create(**kwargs),
                timeout=self.timeout_seconds,
            )
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LLMStreamChunk(delta=chunk.choices[0].delta.content, done=False)

            latency_ms = int((time.perf_counter() - start_ts) * 1000)
            self.circuit_breaker.record_success()
            yield LLMStreamChunk(delta="", done=True, latency_ms=latency_ms)
        except Exception as exc:
            self.circuit_breaker.record_failure()
            raise self._map_exception(exc) from exc

