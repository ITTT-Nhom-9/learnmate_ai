"""Schemas Pydantic cho phân hệ Trắc nghiệm thích ứng AI Quiz (TK-15 / Phân hệ 5).

Tuân thủ:
- Quy tắc BR-04: API trả danh sách câu hỏi làm bài TUYỆT ĐỐI không bao giờ kèm theo đáp án đúng (is_correct)
  hoặc lời giải thích (explanation), chống gian lận trong quá trình làm bài.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.quiz import QuizDifficulty


class QuizGenerateRequest(BaseModel):
    """DTO yêu cầu sinh bộ đề trắc nghiệm thích ứng."""
    model_config = ConfigDict(populate_by_name=True)

    lesson_id: Optional[int] = Field(
        default=None, description="Định danh bài học cần sinh câu hỏi trắc nghiệm"
    )
    topic_id: Optional[int] = Field(
        default=None, description="Định danh chủ đề trọng tâm cần kiểm tra (nếu có)"
    )
    num_questions: int = Field(
        default=5, ge=3, le=10, description="Số lượng câu hỏi trắc nghiệm cần sinh (từ 3 đến 10 câu theo SRS)"
    )
    difficulty: QuizDifficulty = Field(
        default=QuizDifficulty.MEDIUM, description="Độ khó thích ứng: EASY, MEDIUM, HARD"
    )


class QuizOptionPublicOut(BaseModel):
    """Phương án trả lời gửi ra Frontend khi sinh viên làm bài (KHÔNG CÓ is_correct theo BR-04)."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Định danh phương án lựa chọn")
    opt_label: Literal["A", "B", "C", "D"] = Field(
        ..., description="Ký hiệu phương án (A, B, C, D)"
    )
    content: str = Field(..., description="Nội dung phương án lựa chọn")


class QuestionPublicOut(BaseModel):
    """Câu hỏi gửi ra Frontend cho sinh viên làm bài (KHÔNG CÓ explanation theo BR-04)."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Định danh câu hỏi")
    content: str = Field(..., description="Nội dung câu hỏi")
    options: List[QuizOptionPublicOut] = Field(
        ..., description="Danh sách 4 phương án lựa chọn (A, B, C, D)"
    )


class QuizPublicResponse(BaseModel):
    """Phản hồi trả về đề thi trắc nghiệm hoàn chỉnh cho màn hình SCR-05."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Định danh bài quiz vừa được tạo")
    topic_id: int = Field(..., description="Định danh chủ đề")
    title: str = Field(..., description="Tiêu đề bài trắc nghiệm")
    difficulty: str = Field(..., description="Mức độ khó của bài thi")
    total_questions: int = Field(..., description="Tổng số câu hỏi trong bài")
    questions: List[QuestionPublicOut] = Field(
        ..., description="Danh sách các câu hỏi trắc nghiệm an toàn bảo mật"
    )
