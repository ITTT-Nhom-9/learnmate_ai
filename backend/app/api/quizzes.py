"""Router API cho phân hệ Quizzes tại Backend Core (TK-15 / Phân hệ 5).

Endpoints:
- POST /api/v1/quizzes/generate: Sinh bài trắc nghiệm thích ứng từ nội dung bài học.
- POST /api/v1/quiz/generate: Tuyến đường alias hỗ trợ tương thích ngược.
- POST /api/v1/quiz/submit: Nộp bài, chấm điểm tự động thang 10 và lưu lịch sử làm bài (BR-08).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.quiz import (
    QuizGenerateRequest,
    QuizPublicResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services.ai_quiz_client import AIQuizClient, get_ai_quiz_client
from app.services.quiz_service import QuizService
from app.services.quiz_submission_service import QuizSubmissionService

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])
# Router phụ dành cho alias /quiz
alias_router = APIRouter(prefix="/quiz", tags=["Quizzes"])


@router.post(
    "/generate",
    response_model=QuizPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sinh bài trắc nghiệm thích ứng bằng AI từ nội dung bài học (BR-04, BR-06)",
    description=(
        "Cách hoạt động:\n"
        "1. Xác thực sinh viên qua Access Token JWT.\n"
        "2. Kiểm tra bài học hoặc chủ đề và lấy nội dung lý thuyết markdown.\n"
        "3. Gọi AI Microservice sinh câu hỏi 4 lựa chọn (A, B, C, D) với cấu trúc JSON nghiêm ngặt (BR-06).\n"
        "4. Lưu bộ đề, câu hỏi, phương án và đáp án đúng vào CSDL MySQL.\n"
        "5. Trả về danh sách câu hỏi an toàn (TUYỆT ĐỐI không kèm đáp án đúng theo quy tắc bảo mật BR-04)."
    ),
)
async def generate_quiz_endpoint(
    payload: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AIQuizClient = Depends(get_ai_quiz_client),
) -> QuizPublicResponse:
    service = QuizService(db=db, ai_client=ai_client)
    return await service.generate_adaptive_quiz(
        user=current_user,
        lesson_id=payload.lesson_id,
        topic_id=payload.topic_id,
        num_questions=payload.num_questions,
        difficulty=payload.difficulty.value,
    )


@alias_router.post(
    "/generate",
    response_model=QuizPublicResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def generate_quiz_alias_endpoint(
    payload: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AIQuizClient = Depends(get_ai_quiz_client),
) -> QuizPublicResponse:
    return await generate_quiz_endpoint(payload, current_user, db, ai_client)


@alias_router.post(
    "/submit",
    response_model=QuizSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Nộp bài trắc nghiệm và chấm điểm tự động thang 10 (BR-08)",
    description=(
        "Cách hoạt động:\n"
        "1. Xác thực sinh viên qua Access Token JWT.\n"
        "2. Kiểm tra câu hỏi thuộc đề và phương án thuộc câu hỏi; câu không gửi lên được tính là bỏ trống.\n"
        "3. So khớp với đáp án đúng trong CSDL, tính điểm = số câu đúng / tổng số câu × 10.\n"
        "4. Lưu lượt làm bài vào quiz_attempts và đúng/sai từng câu vào attempt_answers.\n"
        "5. Trả về điểm, đáp án đúng và lời giải từng câu (chỉ sau khi đã nộp bài)."
    ),
)
def submit_quiz_endpoint(
    payload: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizSubmitResponse:
    return QuizSubmissionService(db).submit(current_user, payload)
