"""Schemas DTO cho phân hệ học tập gợi mở Socratic Learning (TK-14 / Phân hệ 4).

Tuân thủ quy tắc BR-02:
- Tối đa 5 bước gợi mở: Khám phá -> Thử thách -> Gợi ý -> Củng cố suy luận -> Đánh giá/Tổng kết.
- Tuyệt đối không đưa ra đáp án/lời giải ở các bước 1-4.
- Bước 5 là bước tổng kết, cho phép đưa ra đáp án và đúc kết kiến thức.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tutor_schema import ChatMessageDTO, LLMUsageDTO


MAX_SOCRATIC_STEPS = 5

class SocraticStage(str, Enum):
    """5 giai đoạn định hướng tư duy theo phương pháp sư phạm Socratic."""
    DISCOVER = "DISCOVER"          # Bước 1: Khám phá vấn đề và dữ kiện
    CHALLENGE = "CHALLENGE"        # Bước 2: Thử thách giả định và nguyên lý
    HINT = "HINT"                  # Bước 3: Gợi ý hướng đi khi gặp vướng mắc
    SYNTHESIZE = "SYNTHESIZE"      # Bước 4: Củng cố suy luận và đúc kết
    EVALUATE = "EVALUATE"          # Bước 5: Đánh giá, tổng kết và lời giải


class StudentEvaluation(str, Enum):
    """Đánh giá sơ bộ phản hồi của sinh viên từ mô hình AI."""
    CORRECT = "CORRECT"                      # Sinh viên hiểu đúng và trả lời chính xác
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"  # Sinh viên đúng một phần hoặc có hướng đúng
    WRONG = "WRONG"                          # Sinh viên trả lời sai bản chất
    DONT_KNOW = "DONT_KNOW"                  # Sinh viên bối rối, trả lời không biết


# Tên tiếng Việt chuẩn mực của 5 giai đoạn
STAGE_NAMES = {
    SocraticStage.DISCOVER: "Khám phá",
    SocraticStage.CHALLENGE: "Thử thách",
    SocraticStage.HINT: "Gợi ý",
    SocraticStage.SYNTHESIZE: "Củng cố suy luận",
    SocraticStage.EVALUATE: "Tổng kết",
}

# Bản đồ ánh xạ bước (1..5) sang SocraticStage
STEP_TO_STAGE = {
    1: SocraticStage.DISCOVER,
    2: SocraticStage.CHALLENGE,
    3: SocraticStage.HINT,
    4: SocraticStage.SYNTHESIZE,
    5: SocraticStage.EVALUATE,
}


class SocraticFeedback(BaseModel):
    """Cấu trúc trạng thái phân tích được chuẩn hóa từ câu trả lời Socratic."""
    model_config = ConfigDict(populate_by_name=True)

    step: int = Field(..., ge=1, le=5, description="Nấc bước hiện tại (1..5 theo BR-02)")
    stage: SocraticStage = Field(..., description="Mã giai đoạn Socratic")
    stage_name: str = Field(..., description="Tên giai đoạn hiển thị (tiếng Việt)")
    evaluation: Optional[StudentEvaluation] = Field(
        default=None, description="Đánh giá sơ bộ câu trả lời của sinh viên"
    )
    feedback: str = Field(
        ..., description="Nhận xét ngắn, mang tính động viên hoặc định hướng tư duy"
    )
    guidance_question: Optional[str] = Field(
        default=None,
        description="Một câu hỏi gợi mở duy nhất cho bước tiếp theo (bắt buộc ở bước 1-4)",
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Tổng kết lời giải và kiến thức (chỉ có ở bước 5 / is_concluded=True, None ở bước 1-4 theo BR-02)",
    )
    is_concluded: bool = Field(
        default=False,
        description="Cờ đánh dấu kết thúc phiên Socratic (True khi đạt bước 5 hoặc giải đúng)",
    )
    wrong_streak: int = Field(
        default=0,
        ge=0,
        description="Số lần trả lời sai hoặc không biết liên tiếp",
    )


class SocraticStepRequest(BaseModel):
    """DTO gửi yêu cầu gợi mở Socratic từ Backend Core sang AI Microservice."""
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(..., min_length=1, max_length=4000, description="Nội dung câu hỏi/phản hồi của sinh viên")
    lesson_context: Optional[str] = Field(
        default=None, max_length=10000, description="Ngữ cảnh tóm tắt lý thuyết bài học"
    )
    history: List[ChatMessageDTO] = Field(
        default_factory=list, description="Lịch sử các lượt đối thoại trước trong phiên chat"
    )
    current_step: int = Field(
        default=1, ge=1, le=5, description="Cấp độ gợi mở hiện tại của phiên (1..5)"
    )
    wrong_streak: int = Field(
        default=0, ge=0, description="Số lần sai liên tiếp đã tích lũy trong phiên"
    )
    temperature: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Độ sáng tạo của mô hình (thấp để bám sát logic sư phạm)"
    )
    max_tokens: Optional[int] = Field(
        default=1024, ge=64, le=4096, description="Giới hạn số token tối đa cho câu phản hồi"
    )


class SocraticStepResponse(BaseModel):
    """DTO phản hồi kết quả Socratic hoàn chỉnh từ AI Microservice."""
    model_config = ConfigDict(populate_by_name=True)

    reply: str = Field(..., description="Nội dung phản hồi Markdown hiển thị cho người học")
    feedback: SocraticFeedback = Field(..., description="Cấu trúc trạng thái phân tích ngữ nghĩa")
    provider: str = Field(..., description="Nhà cung cấp LLM (gemini / openai)")
    model: str = Field(..., description="Tên mô hình ngôn ngữ lớn đã thực thi")
    usage: LLMUsageDTO = Field(..., description="Thống kê tài nguyên tiêu thụ")
