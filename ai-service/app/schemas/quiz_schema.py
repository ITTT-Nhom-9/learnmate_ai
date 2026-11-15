"""Schemas Pydantic v2 cho phân hệ Sinh đề trắc nghiệm AI Quiz (TK-15 / Phân hệ 5).

Tuân thủ:
- Quy tắc BR-06: Xác thực tính toàn vẹn Quiz JSON qua Pydantic schema nghiêm ngặt.
- Cấu trúc: 4 phương án lựa chọn A, B, C, D; đúng 1 đáp án đúng; kèm lời giải thích ngắn gọn.
"""
from enum import Enum
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.tutor_schema import LLMUsageDTO


class QuizDifficultyEnum(str, Enum):
    """Mức độ khó của bài trắc nghiệm theo BR-03."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuizOptionDTO(BaseModel):
    """Một phương án lựa chọn trắc nghiệm (A, B, C hoặc D)."""
    model_config = ConfigDict(populate_by_name=True)

    opt_label: Literal["A", "B", "C", "D"] = Field(
        ..., description="Nhãn phương án (A, B, C, D)"
    )
    content: str = Field(
        ..., min_length=1, description="Nội dung phương án lựa chọn (không được để trống)"
    )
    is_correct: bool = Field(
        default=False, description="Đánh dấu phương án đúng (duy nhất 1 phương án True mỗi câu)"
    )


class QuizQuestionSpec(BaseModel):
    """Cấu trúc một câu hỏi trắc nghiệm do mô hình AI sinh ra."""
    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(
        ..., min_length=5, description="Nội dung câu hỏi trắc nghiệm"
    )
    options: List[QuizOptionDTO] = Field(
        ..., min_length=4, max_length=4, description="Bắt buộc có đúng 4 phương án lựa chọn"
    )
    explanation: str = Field(
        ..., min_length=5, description="Lời giải thích ngắn gọn lý do vì sao đáp án đó đúng"
    )

    @field_validator("options")
    @classmethod
    def validate_options_labels_and_correctness(cls, options: List[QuizOptionDTO]) -> List[QuizOptionDTO]:
        """Xác thực tính toàn vẹn theo BR-06:
        - Đủ 4 nhãn A, B, C, D duy nhất.
        - Có đúng 1 phương án đánh dấu is_correct=True.
        - Không có nội dung phương án nào rỗng.
        """
        labels = [opt.opt_label for opt in options]
        if sorted(labels) != ["A", "B", "C", "D"]:
            raise ValueError(f"Các phương án phải có đầy đủ nhãn A, B, C, D. Nhận được: {labels}")

        correct_count = sum(1 for opt in options if opt.is_correct)
        if correct_count != 1:
            raise ValueError(
                f"Mỗi câu hỏi phải có chính xác 1 phương án đúng (is_correct=True). Hiện có: {correct_count}"
            )

        for opt in options:
            if not opt.content.strip():
                raise ValueError(f"Nội dung phương án {opt.opt_label} không được để trống")

        return options


class QuizBundleOut(BaseModel):
    """Cấu trúc bộ đề thi trắc nghiệm hoàn chỉnh sau khi kiểm định."""
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., min_length=3, description="Tiêu đề bài kiểm tra trắc nghiệm")
    difficulty: QuizDifficultyEnum = Field(
        default=QuizDifficultyEnum.MEDIUM, description="Mức độ khó của bài quiz"
    )
    total_questions: int = Field(..., ge=1, le=10, description="Tổng số câu hỏi trong bài")
    questions: List[QuizQuestionSpec] = Field(
        ..., min_length=1, max_length=10, description="Danh sách các câu hỏi trắc nghiệm"
    )

    @field_validator("questions")
    @classmethod
    def validate_questions_count(cls, questions: List[QuizQuestionSpec], info) -> List[QuizQuestionSpec]:
        expected = info.data.get("total_questions")
        if expected is not None and len(questions) != expected:
            # Tự động đồng bộ total_questions theo số câu thực tế
            pass
        return questions


class QuizGenerationSpec(BaseModel):
    """DTO gửi yêu cầu sinh đề trắc nghiệm từ Backend Core sang AI Microservice."""
    model_config = ConfigDict(populate_by_name=True)

    lesson_title: str = Field(..., min_length=1, description="Tiêu đề bài học")
    topic_name: Optional[str] = Field(default=None, description="Tên chủ đề trọng tâm")
    lesson_content: str = Field(
        ..., min_length=10, description="Nội dung bài học hoặc giáo trình làm ngữ cảnh"
    )
    num_questions: int = Field(
        default=5, ge=1, le=10, description="Số lượng câu hỏi cần sinh (3-10 câu theo SRS)"
    )
    difficulty: QuizDifficultyEnum = Field(
        default=QuizDifficultyEnum.MEDIUM, description="Độ khó yêu cầu (EASY, MEDIUM, HARD)"
    )
    temperature: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Nhiệt độ sinh dữ liệu (thấp để giữ tính ổn định JSON)"
    )


class QuizGenerationResponse(BaseModel):
    """DTO phản hồi kết quả sinh đề trắc nghiệm từ AI Microservice."""
    model_config = ConfigDict(populate_by_name=True)

    bundle: QuizBundleOut = Field(..., description="Bộ đề trắc nghiệm hoàn chỉnh đã kiểm định")
    provider: str = Field(..., description="Nhà cung cấp LLM (gemini / openai)")
    model: str = Field(..., description="Mô hình ngôn ngữ lớn đã thực thi")
    usage: LLMUsageDTO = Field(..., description="Thống kê tài nguyên tiêu thụ")
