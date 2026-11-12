import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

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

logger = logging.getLogger("ai-service.gemini")

_RETRYABLE_GOOGLE_EXCEPTIONS = (
    google_exceptions.ResourceExhausted,
    google_exceptions.ServiceUnavailable,
    google_exceptions.InternalServerError,
    google_exceptions.DeadlineExceeded,
)


class GeminiAdapter(LLMProvider):
    """Adapter kết nối Google Gemini SDK hỗ trợ chat, streaming SSE và cơ chế resilience."""

    provider_name: str = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else settings.GEMINI_API_KEY) or ""
        self.model_name = (model_name or settings.LLM_MODEL or "gemini-3.5-flash-lite").strip()
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.AI_TIMEOUT_SECONDS
        )
        self.max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=settings.CIRCUIT_BREAKER_THRESHOLD,
            reset_timeout=settings.CIRCUIT_BREAKER_RESET_SECONDS,
        )

    def __repr__(self) -> str:
        return f"<GeminiAdapter(model='{self.model_name}', configured={bool(self._api_key.strip())})>"

    def _ensure_configured(self) -> None:
        if not self._api_key.strip():
            raise LLMConfigurationError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=self._api_key)

    @staticmethod
    def _build_payload(
        messages: List[LLMMessage], system_prompt: Optional[str]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Tách system instruction và ánh xạ hội thoại sang định dạng Google Gemini."""
        system_parts: List[str] = []
        if system_prompt and system_prompt.strip():
            system_parts.append(system_prompt.strip())

        contents: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                if msg.content.strip():
                    system_parts.append(msg.content.strip())
                continue
            gemini_role = "model" if msg.role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [msg.content]})

        if not contents:
            raise AIException(
                message="At least one user or assistant message is required",
                status_code=400,
                error_code="EMPTY_MESSAGES",
            )

        merged_system = "\n\n".join(system_parts) if system_parts else None
        return merged_system, contents

    @staticmethod
    def _build_generation_config(
        temperature: float,
        max_tokens: Optional[int],
        response_mime_type: Optional[str] = None,
    ) -> genai.types.GenerationConfig:
        kwargs: Dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if response_mime_type:
            kwargs["response_mime_type"] = response_mime_type
        return genai.types.GenerationConfig(**kwargs)

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Trích xuất văn bản an toàn từ phản hồi Gemini."""
        try:
            text = response.text
            if text is not None:
                return text
        except (ValueError, AttributeError):
            pass

        candidates = getattr(response, "candidates", None) or []
        parts_text: List[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    parts_text.append(part_text)
        return "".join(parts_text)

    @staticmethod
    def _extract_usage(response: Any) -> Tuple[int, int, int]:
        """Trích xuất số lượng token tiêu thụ từ usage_metadata."""
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return 0, 0, 0
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_tokens = int(
            getattr(usage, "total_token_count", 0) or (prompt_tokens + completion_tokens)
        )
        return prompt_tokens, completion_tokens, total_tokens

    @staticmethod
    def _map_exception(exc: Exception) -> AIException:
        """Chuyển đổi lỗi SDK sang AIException đã ẩn thông tin nhạy cảm."""
        if isinstance(exc, AIException):
            return exc

        safe_msg = mask_sensitive_text(str(exc))
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError, google_exceptions.DeadlineExceeded)):
            return LLMTimeoutError(f"Gemini request timed out: {safe_msg}")
        if isinstance(exc, google_exceptions.ResourceExhausted):
            return LLMRateLimitError(f"Gemini API rate limit exceeded: {safe_msg}")
        if isinstance(exc, (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated)):
            return LLMConfigurationError("Gemini API authentication failed; verify GEMINI_API_KEY")
        if isinstance(exc, google_exceptions.InvalidArgument):
            return AIException(
                message=f"Invalid request to Gemini model: {safe_msg}",
                status_code=400,
                error_code="LLM_INVALID_ARGUMENT",
            )
        return LLMUpstreamError(f"Gemini API error: {safe_msg}")

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
            return True
        if isinstance(exc, _RETRYABLE_GOOGLE_EXCEPTIONS):
            return True
        msg_lower = str(exc).lower()
        return any(code in msg_lower for code in ("429", "500", "503", "resource exhausted", "timeout"))

    def _create_model(self, system_instruction: Optional[str]) -> genai.GenerativeModel:
        kwargs: Dict[str, Any] = {"model_name": self.model_name}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        return genai.GenerativeModel(**kwargs)

    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        self._ensure_configured()
        self.circuit_breaker.ensure_closed()

        system_instruction, contents = self._build_payload(messages, system_prompt)
        generation_config = self._build_generation_config(
            temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type=response_mime_type,
        )
        model = self._create_model(system_instruction)

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            start_ts = time.perf_counter()
            try:
                response = await asyncio.wait_for(
                    model.generate_content_async(
                        contents,
                        generation_config=generation_config,
                        request_options={"timeout": self.timeout_seconds},
                    ),
                    timeout=self.timeout_seconds,
                )
                latency_ms = int((time.perf_counter() - start_ts) * 1000)
                content_text = self._extract_text(response)
                prompt_tok, comp_tok, total_tok = self._extract_usage(response)
                self.circuit_breaker.record_success()
                return LLMResponse(
                    content=content_text,
                    provider=self.provider_name,
                    model=self.model_name,
                    tokens_prompt=prompt_tok,
                    tokens_completion=comp_tok,
                    total_tokens=total_tok,
                    latency_ms=latency_ms,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Gemini chat attempt %d/%d failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    mask_sensitive_text(str(exc)),
                )
                if attempt < self.max_retries and self._is_retryable(exc):
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                self.circuit_breaker.record_failure()
                raise self._map_exception(exc) from exc

        self.circuit_breaker.record_failure()
        raise self._map_exception(last_exc or RuntimeError("Unknown Gemini failure"))

    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        self._ensure_configured()
        self.circuit_breaker.ensure_closed()

        system_instruction, contents = self._build_payload(messages, system_prompt)
        generation_config = self._build_generation_config(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        model = self._create_model(system_instruction)

        start_ts = time.perf_counter()
        prompt_tok = 0
        comp_tok = 0
        total_tok = 0

        try:
            response_stream = await asyncio.wait_for(
                model.generate_content_async(
                    contents,
                    generation_config=generation_config,
                    stream=True,
                    request_options={"timeout": self.timeout_seconds},
                ),
                timeout=self.timeout_seconds,
            )
            async for chunk in response_stream:
                delta = self._extract_text(chunk)
                p_t, c_t, t_t = self._extract_usage(chunk)
                if t_t > 0 or p_t > 0 or c_t > 0:
                    prompt_tok, comp_tok, total_tok = p_t, c_t, t_t
                if delta:
                    yield LLMStreamChunk(delta=delta, done=False)

            latency_ms = int((time.perf_counter() - start_ts) * 1000)
            self.circuit_breaker.record_success()
            yield LLMStreamChunk(
                delta="",
                done=True,
                tokens_prompt=prompt_tok,
                tokens_completion=comp_tok,
                total_tokens=total_tok,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            self.circuit_breaker.record_failure()
            logger.warning("Gemini stream failed: %s", mask_sensitive_text(str(exc)))
            raise self._map_exception(exc) from exc

