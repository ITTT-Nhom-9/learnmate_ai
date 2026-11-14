from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Ten truong bam sat sheet "Dac ta API & Figma UI UX" (API-09, API-10).


# ------------------------------------------------------------------------------
# API-09: POST /tutor/chat (SSE)
# ------------------------------------------------------------------------------

class TutorChatRequest(BaseModel):
    lesson_id: int = Field(..., ge=1)
    message: str = Field(..., min_length=1, max_length=4000, description="Câu hỏi của sinh viên")
    mode: Literal["EXPLAIN", "SOCRATIC"] = "EXPLAIN"

    @field_validator("message")
    @classmethod
    def _strip_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Câu hỏi không được để trống")
        return v


# ------------------------------------------------------------------------------
# API-10: GET /tutor/history/{lesson_id}?limit=20
# ------------------------------------------------------------------------------

class ChatMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    tokens_used: int = 0
    created_at: datetime


class TutorHistoryResponse(BaseModel):
    session_id: int | None = None
    lesson_id: int
    mode: str | None = None
    hint_level: int = 0
    status: str | None = None
    quota_remaining: int
    messages: list[ChatMessageItem]
