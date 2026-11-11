from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChatMessageDTO(BaseModel):
    """Một lượt tin nhắn trong lịch sử hội thoại gửi từ Backend."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)


class TutorRequestDTO(BaseModel):
    """Dữ liệu đầu vào chuẩn cho endpoint gọi AI Tutor nội bộ."""

    message: str = Field(..., min_length=1, max_length=10000, description="Câu hỏi của sinh viên")
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt tùy chỉnh (sẽ được nạp từ template ở TK-11/TK-12)",
    )
    lesson_context: Optional[str] = Field(
        default=None,
        description="Ngữ cảnh bài học hiện tại (tên bài học, nội dung lý thuyết tóm tắt)",
    )
    history: List[ChatMessageDTO] = Field(
        default_factory=list,
        description="Tối đa 10 tin nhắn gần nhất để duy trì ngữ cảnh hội thoại",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)
    response_mime_type: Optional[Literal["text/plain", "application/json"]] = None


class LLMUsageDTO(BaseModel):
    """Thông tin kiểm toán token và thời gian phản hồi LLM."""

    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_tokens: int = 0
    latency_ms: int = 0


class TutorResponseDTO(BaseModel):
    """Phản hồi chuẩn hóa từ AI Microservice trả về Backend."""

    reply: str
    provider: str
    model: str
    usage: LLMUsageDTO

