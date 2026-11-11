from abc import ABC, abstractmethod
from dataclasses import dataclass
import time
from typing import AsyncIterator, List, Literal, Optional
from app.core.exceptions import CircuitBreakerOpenError


@dataclass
class LLMMessage:
    """Thông điệp hội thoại chuẩn hóa dùng chung giữa các LLM Adapter."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class LLMResponse:
    """Kết quả trả về chuẩn hóa cho cuộc gọi LLM không streaming."""

    content: str
    provider: str
    model: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_tokens: int = 0
    latency_ms: int = 0


@dataclass
class LLMStreamChunk:
    """Đoạn dữ liệu văn bản trả về theo luồng (Streaming SSE)."""

    delta: str
    done: bool = False
    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_tokens: int = 0
    latency_ms: int = 0


class CircuitBreaker:
    """Bảo vệ dịch vụ trước chuỗi lỗi liên tiếp từ nhà cung cấp LLM bên ngoài."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.opened_at: Optional[float] = None

    def ensure_closed(self) -> None:
        """Kiểm tra trạng thái mạch trước khi cho phép gọi API LLM."""
        if self.opened_at is None:
            return
        elapsed = time.monotonic() - self.opened_at
        if elapsed >= self.reset_timeout:
            # Chuyển sang half-open: cho phép thử lại 1 yêu cầu mới
            return
        raise CircuitBreakerOpenError(
            f"AI Circuit Breaker is open; retry after {int(self.reset_timeout - elapsed) + 1}s"
        )

    def record_success(self) -> None:
        """Đặt lại bộ đếm lỗi sau một phản hồi thành công."""
        self.failure_count = 0
        self.opened_at = None

    def record_failure(self) -> None:
        """Tăng bộ đếm lỗi và mở mạch nếu vượt ngưỡng."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = time.monotonic()


class LLMProvider(ABC):
    """Lớp trừu tượng chuẩn Adapter Pattern cho các nhà cung cấp mô hình ngôn ngữ lớn."""

    provider_name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        """Gửi danh sách tin nhắn và trả về phản hồi hoàn chỉnh."""
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Gửi danh sách tin nhắn và phát dần từng đoạn văn bản phản hồi (SSE)."""
        raise NotImplementedError
        yield  # pragma: no cover

