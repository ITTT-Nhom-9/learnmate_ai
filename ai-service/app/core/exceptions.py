import logging
import re
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.core.config import settings

logger = logging.getLogger("ai-service")

_API_KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{10,}"),
    re.compile(r"sk-[0-9A-Za-z\-_]{10,}"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([^\s,;\"']+)"),
]


def mask_sensitive_text(text: str) -> str:
    """Ẩn các khóa API nhạy cảm khỏi thông điệp lỗi và log trước khi ghi nhận hoặc phản hồi."""
    if not text:
        return text

    masked = text
    for secret_val in (
        settings.GEMINI_API_KEY,
        settings.OPENAI_API_KEY,
        settings.INTERNAL_API_KEY,
    ):
        if secret_val and len(secret_val) >= 4:
            masked = masked.replace(secret_val, "***REDACTED***")

    for idx, pattern in enumerate(_API_KEY_PATTERNS):
        if idx == 2:
            masked = pattern.sub(r"\1***REDACTED***", masked)
        else:
            masked = pattern.sub("***REDACTED***", masked)

    return masked


class AIException(Exception):
    """Ngoại lệ cơ sở cho các lỗi phát sinh trong AI Microservice."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        error_code: str = "AI_SERVICE_ERROR",
    ) -> None:
        self.message = mask_sensitive_text(message)
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class LLMConfigurationError(AIException):
    """Thiếu hoặc sai cấu hình nhà cung cấp LLM / API Key."""

    def __init__(self, message: str = "LLM provider is not properly configured") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="LLM_CONFIGURATION_ERROR",
        )


class LLMTimeoutError(AIException):
    """Quá thời gian chờ phản hồi từ Cloud LLM."""

    def __init__(self, message: str = "LLM request timed out, please try again later") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="LLM_TIMEOUT",
        )


class LLMRateLimitError(AIException):
    """Vượt hạn mức gọi API của nhà cung cấp LLM (429)."""

    def __init__(self, message: str = "LLM provider rate limit exceeded, please retry later") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="LLM_RATE_LIMIT",
        )


class CircuitBreakerOpenError(AIException):
    """Circuit Breaker đang mở do chuỗi lỗi liên tiếp từ nhà cung cấp LLM."""

    def __init__(self, message: str = "AI service temporarily unavailable due to circuit breaker") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="CIRCUIT_BREAKER_OPEN",
        )


class LLMUpstreamError(AIException):
    """Lỗi phản hồi không mong đợi từ Cloud LLM."""

    def __init__(self, message: str = "Upstream LLM provider returned an error") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="LLM_UPSTREAM_ERROR",
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký bộ lọc ngoại lệ toàn cục cho ứng dụng FastAPI AI Microservice."""

    @app.exception_handler(AIException)
    async def handle_ai_exception(request: Request, exc: AIException) -> JSONResponse:
        logger.warning(
            "AIException [%s] on %s %s: %s",
            exc.error_code,
            request.method,
            request.url.path,
            mask_sensitive_text(exc.message),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "detail": exc.message,
            },
        )

