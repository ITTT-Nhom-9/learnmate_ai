"""Nghiệp vụ Sinh đề trắc nghiệm thích ứng AI Quiz (TK-15 / Phân hệ 5).

Chịu trách nhiệm:
- Thu thập ngữ cảnh bài học và chủ đề từ CSDL.
- Gọi AI Microservice sinh đề trắc nghiệm theo schema JSON chuẩn (BR-06).
- Lưu trữ bộ đề thi gồm các thực thể: Quiz, Question, QuestionOption vào CSDL MySQL.
- Định dạng và lọc bỏ trường is_correct & explanation khi trả về phía Client theo quy tắc bảo mật đề thi BR-04.
"""
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import ContentType, Course, CourseStatus, Lesson, Topic
from app.models.quiz import Question, QuestionOption, Quiz, QuizDifficulty
from app.models.user import User
from app.schemas.quiz import (
    QuestionPublicOut,
    QuizOptionPublicOut,
    QuizPublicResponse,
)
from app.services.ai_quiz_client import AIQuizClient, AIQuizServiceError


class QuizService:
    def __init__(self, db: Session, ai_client: AIQuizClient):
        self.db = db
        self.ai_client = ai_client

    async def generate_adaptive_quiz(
        self,
        user: User,
        lesson_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        num_questions: int = 5,
        difficulty: str = QuizDifficulty.MEDIUM.value,
    ) -> QuizPublicResponse:
        """
        Sinh bài trắc nghiệm mới từ AI, lưu vào DB và trả về đề thi an toàn (không có đáp án đúng).
        """
        if not lesson_id and not topic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cần cung cấp ít nhất lesson_id hoặc topic_id để sinh đề thi",
            )

        lesson: Optional[Lesson] = None
        topic: Optional[Topic] = None

        # 1. Tìm theo topic_id nếu được truyền
        if topic_id:
            topic = self.db.scalar(
                select(Topic)
                .options(selectinload(Topic.lesson).selectinload(Lesson.contents))
                .where(Topic.id == topic_id)
            )
            if not topic:
                raise HTTPException(status_code=404, detail="Chủ đề kiến thức không tồn tại")
            lesson = topic.lesson

        # 2. Hoặc tìm theo lesson_id
        elif lesson_id:
            lesson = self.db.scalar(
                select(Lesson)
                .join(Course, Course.id == Lesson.course_id)
                .options(selectinload(Lesson.topics), selectinload(Lesson.contents))
                .where(Lesson.id == lesson_id, Course.status == CourseStatus.ACTIVE.value)
            )
            if not lesson:
                raise HTTPException(status_code=404, detail="Bài học không tồn tại hoặc đã bị ẩn")

            if lesson.topics:
                topic = lesson.topics[0]
            else:
                # Tạo chủ đề mặc định nếu bài học chưa có chủ đề
                topic = Topic(
                    lesson_id=lesson.id,
                    name=lesson.title,
                    description=lesson.title,
                )
                self.db.add(topic)
                self.db.flush()

        # 3. Thu thập nội dung lý thuyết
        contents = [
            c.body
            for c in (lesson.contents if lesson else [])
            if c.content_type == ContentType.MARKDOWN.value and c.body
        ]
        body_text = "\n\n".join(contents).strip()
        if not body_text:
            body_text = f"Nội dung trọng tâm: {lesson.title}. Chủ đề: {topic.name}."

        # 4. Gửi yêu cầu sang AI Microservice
        ai_payload = {
            "lesson_title": lesson.title,
            "topic_name": topic.name,
            "lesson_content": body_text[:8000],
            "num_questions": num_questions,
            "difficulty": difficulty,
        }

        try:
            ai_response = await self.ai_client.generate_quiz(ai_payload)
        except AIQuizServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message)

        bundle = ai_response.get("bundle") or {}
        raw_questions = bundle.get("questions") or []
        if not raw_questions:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Dịch vụ AI không trả về danh sách câu hỏi hợp lệ",
            )

        # 5. Lưu vào CSDL MySQL (Bảo mật: lưu is_correct và explanation tại DB)
        quiz_title = bundle.get("title") or f"Trắc nghiệm: {topic.name}"
        quiz_record = Quiz(
            topic_id=topic.id,
            title=quiz_title,
            difficulty=difficulty,
            total_questions=len(raw_questions),
        )
        self.db.add(quiz_record)
        self.db.flush()

        public_questions: list[QuestionPublicOut] = []

        for q_data in raw_questions:
            question_record = Question(
                quiz_id=quiz_record.id,
                content=q_data["content"],
                explanation=q_data.get("explanation", ""),
            )
            self.db.add(question_record)
            self.db.flush()

            public_options: list[QuizOptionPublicOut] = []
            for opt_data in q_data.get("options", []):
                option_record = QuestionOption(
                    question_id=question_record.id,
                    opt_label=opt_data["opt_label"],
                    content=opt_data["content"],
                    is_correct=bool(opt_data.get("is_correct", False)),
                )
                self.db.add(option_record)
                self.db.flush()

                # Quy tắc BR-04: Tạo DTO trả ra Client KHÔNG CÓ is_correct
                public_options.append(
                    QuizOptionPublicOut(
                        id=option_record.id,
                        opt_label=option_record.opt_label,
                        content=option_record.content,
                    )
                )

            # Quy tắc BR-04: Tạo DTO trả ra Client KHÔNG CÓ explanation khi thi
            public_questions.append(
                QuestionPublicOut(
                    id=question_record.id,
                    content=question_record.content,
                    options=public_options,
                )
            )

        self.db.commit()

        return QuizPublicResponse(
            id=quiz_record.id,
            topic_id=quiz_record.topic_id,
            title=quiz_record.title,
            difficulty=quiz_record.difficulty,
            total_questions=quiz_record.total_questions,
            questions=public_questions,
        )
