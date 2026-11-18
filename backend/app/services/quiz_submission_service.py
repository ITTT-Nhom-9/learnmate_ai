"""Nghiệp vụ Nộp bài & Chấm điểm trắc nghiệm tự động (Phân hệ 5 / BR-08).

Chịu trách nhiệm:
- Kiểm tra tính hợp lệ của bài nộp (câu hỏi thuộc đề, phương án thuộc câu hỏi, không trùng câu).
- So khớp phương án đã chọn với đáp án đúng lưu trong CSDL.
- Tính điểm thang 10: score = số câu đúng / tổng số câu của đề * 10 (làm tròn 2 chữ số).
- Lưu lượt làm bài vào quiz_attempts và chi tiết đúng/sai từng câu vào attempt_answers.
"""
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.quiz import (
    AttemptAnswer,
    Question,
    Quiz,
    QuizAttempt,
    QuizAttemptStatus,
)
from app.models.user import User
from app.schemas.quiz import AnswerResultOut, QuizSubmitRequest, QuizSubmitResponse

MAX_SCORE = Decimal("10")


def calculate_score(correct_count: int, total_questions: int) -> Decimal:
    """Điểm thang 10, làm tròn 2 chữ số thập phân (ROUND_HALF_UP)."""
    if total_questions <= 0:
        return Decimal("0.00")
    raw = Decimal(correct_count) / Decimal(total_questions) * MAX_SCORE
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class QuizSubmissionService:
    def __init__(self, db: Session):
        self.db = db

    def submit(self, user: User, payload: QuizSubmitRequest) -> QuizSubmitResponse:
        quiz = self.db.scalar(
            select(Quiz)
            .options(selectinload(Quiz.questions).selectinload(Question.options))
            .where(Quiz.id == payload.quiz_id)
        )
        if quiz is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bài trắc nghiệm không tồn tại")
        if not quiz.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Bài trắc nghiệm chưa có câu hỏi"
            )

        questions_by_id = {q.id: q for q in quiz.questions}

        # 1. Kiểm tra bài nộp
        selected_by_question: dict[int, int | None] = {}
        for ans in payload.answers:
            if ans.question_id in selected_by_question:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Câu hỏi {ans.question_id} được nộp nhiều lần",
                )
            question = questions_by_id.get(ans.question_id)
            if question is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Câu hỏi {ans.question_id} không thuộc bài trắc nghiệm này",
                )
            if ans.selected_option_id is not None and all(
                opt.id != ans.selected_option_id for opt in question.options
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Phương án {ans.selected_option_id} không thuộc câu hỏi {ans.question_id}",
                )
            selected_by_question[ans.question_id] = ans.selected_option_id

        # 2. Tạo lượt làm bài
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=user.id,
            score=Decimal("0.00"),
            duration_sec=payload.duration_sec,
            status=QuizAttemptStatus.SUBMITTED.value,
        )
        self.db.add(attempt)
        self.db.flush()

        # 3. Chấm từng câu (kể cả câu bỏ trống) và lưu chi tiết
        results: list[AnswerResultOut] = []
        correct_count = 0
        unanswered_count = 0
        for question in quiz.questions:
            selected_id = selected_by_question.get(question.id)
            correct_opt = next((o for o in question.options if o.is_correct), None)
            selected_opt = next((o for o in question.options if o.id == selected_id), None)
            is_correct = selected_opt is not None and selected_opt.is_correct

            if selected_opt is None:
                unanswered_count += 1
            if is_correct:
                correct_count += 1

            self.db.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    selected_option_id=selected_id,
                    is_correct=is_correct,
                )
            )
            results.append(
                AnswerResultOut(
                    question_id=question.id,
                    selected_option_id=selected_id,
                    selected_label=selected_opt.opt_label if selected_opt else None,
                    correct_option_id=correct_opt.id if correct_opt else None,
                    correct_label=correct_opt.opt_label if correct_opt else None,
                    is_correct=is_correct,
                    explanation=question.explanation or "",
                )
            )

        total = len(quiz.questions)
        score = calculate_score(correct_count, total)
        attempt.score = score
        self.db.commit()

        # Cập nhật điểm Mastery EMA thích ứng sau khi nộp bài (TK-20 / BR-01, BR-08)
        if quiz.topic_id:
            try:
                from app.services.mastery_service import MasteryService

                MasteryService(self.db).update_mastery_after_quiz(
                    user_id=user.id,
                    topic_id=quiz.topic_id,
                    quiz_score=float(score),
                    duration_sec=payload.duration_sec,
                )
            except Exception as exc:
                import logging

                logging.getLogger(__name__).warning(
                    "Không thể cập nhật Mastery sau khi nộp bài quiz: %s", exc
                )

        return QuizSubmitResponse(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            score=float(score),
            total_questions=total,
            correct_count=correct_count,
            wrong_count=total - correct_count,
            unanswered_count=unanswered_count,
            duration_sec=attempt.duration_sec,
            status=attempt.status,
            answers=results,
        )

    def get_attempt(self, user: User, attempt_id: int) -> QuizSubmitResponse:
        attempt = self.db.scalar(
            select(QuizAttempt)
            .options(
                selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(Question.options),
                selectinload(QuizAttempt.answers),
            )
            .where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user.id)
        )
        if attempt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lượt làm bài không tồn tại")

        quiz = attempt.quiz
        answers_by_qid = {ans.question_id: ans for ans in attempt.answers}

        results: list[AnswerResultOut] = []
        correct_count = 0
        unanswered_count = 0
        for question in quiz.questions:
            ans_record = answers_by_qid.get(question.id)
            selected_id = ans_record.selected_option_id if ans_record else None
            correct_opt = next((o for o in question.options if o.is_correct), None)
            selected_opt = next((o for o in question.options if o.id == selected_id), None)
            is_correct = selected_opt is not None and selected_opt.is_correct

            if selected_opt is None:
                unanswered_count += 1
            if is_correct:
                correct_count += 1

            results.append(
                AnswerResultOut(
                    question_id=question.id,
                    selected_option_id=selected_id,
                    selected_label=selected_opt.opt_label if selected_opt else None,
                    correct_option_id=correct_opt.id if correct_opt else None,
                    correct_label=correct_opt.opt_label if correct_opt else None,
                    is_correct=is_correct,
                    explanation=question.explanation or "",
                )
            )

        total = len(quiz.questions)
        return QuizSubmitResponse(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            score=float(attempt.score),
            total_questions=total,
            correct_count=correct_count,
            wrong_count=total - correct_count,
            unanswered_count=unanswered_count,
            duration_sec=attempt.duration_sec,
            status=attempt.status,
            answers=results,
        )
