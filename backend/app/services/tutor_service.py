"""Nghiep vu AI Tutor (TK-12): quan ly phien chat, luu lich su va ap QuotaGuard (BR-05)."""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import utcnow
from app.models.chat import ChatMessage, ChatMode, ChatRole, ChatSession, ChatSessionStatus
from app.models.course import Course, CourseStatus, Lesson
from app.models.user import User
from app.services.quota_guard import QuotaGuard
from app.services.socratic_service import SocraticEngine, SOCRATIC_MAX_STEPS
# Gioi han do dai ngu canh bai hoc gui sang AI service (tranh prompt qua dai)
LESSON_CONTEXT_MAX_CHARS = 6000

_AI_ROLE = {ChatRole.USER.value: "user", ChatRole.ASSISTANT.value: "assistant"}


class TutorError(Exception):
    status_code: int = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LessonNotFoundError(TutorError):
    status_code = 404


@dataclass
class PreparedTurn:
    """Ket qua buoc chuan bi 1 luot hoi, truoc khi stream cau tra loi tu AI."""

    session_id: int
    user_message_id: int
    mode: str
    hint_level: int
    previous_hint_level: int
    quota_remaining: int  # so luot con lai SAU khi tinh cau hoi nay
    ai_payload: dict = field(default_factory=dict)

    @property
    def is_concluded(self) -> bool:
        return self.mode == ChatMode.SOCRATIC.value and self.hint_level >= SOCRATIC_MAX_STEPS


class TutorService:
    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------------------------------
    # POST /tutor/chat - buoc 1: kiem tra, luu cau hoi, ráp payload cho AI
    # --------------------------------------------------------------------------
    def prepare_turn(self, user: User, lesson_id: int, message: str, mode: str) -> PreparedTurn:
        lesson = self._get_lesson(lesson_id, with_content=True)
        remaining = QuotaGuard(self.db).ensure_available(user.id)

        session = self._get_or_create_session(user.id, lesson.id, mode)
        history = self._recent_messages(session.id, settings.TUTOR_HISTORY_WINDOW)

        previous_hint_level = session.hint_level or 0
        if mode == ChatMode.SOCRATIC.value:
            instruction = SocraticEngine.evaluate_next_step(session)
            session.hint_level = instruction.hint_level

        user_msg = ChatMessage(
            session_id=session.id,
            role=ChatRole.USER.value,
            content=message,
            tokens_used=0,
            created_at=utcnow(),
        )
        self.db.add(user_msg)
        self.db.commit()

        return PreparedTurn(
            session_id=session.id,
            user_message_id=user_msg.id,
            mode=mode,
            hint_level=session.hint_level,
            previous_hint_level=previous_hint_level,
            quota_remaining=remaining - 1,
            ai_payload={
                "message": message,
                "lesson_context": self._lesson_context(lesson, mode, session.hint_level),
                "history": [
                    {"role": _AI_ROLE[m.role], "content": m.content}
                    for m in history
                    if m.role in _AI_ROLE and m.content
                ],
            },
        )

    # --------------------------------------------------------------------------
    # POST /tutor/chat - buoc 2: luu cau tra loi sau khi stream xong
    # --------------------------------------------------------------------------
    def save_reply(self, turn: PreparedTurn, content: str, tokens_used: int) -> int:
        reply = ChatMessage(
            session_id=turn.session_id,
            role=ChatRole.ASSISTANT.value,
            content=content,
            tokens_used=tokens_used,
            created_at=utcnow(),
        )
        self.db.add(reply)
        if turn.is_concluded:
            session = self.db.get(ChatSession, turn.session_id)
            if session is not None:
                session.status = ChatSessionStatus.COMPLETED.value
        self.db.commit()
        return reply.id

    def cancel_turn(self, turn: PreparedTurn) -> None:
        """AI loi va chua sinh duoc noi dung: xoa cau hoi (hoan quota) va tra lai hint_level."""
        msg = self.db.get(ChatMessage, turn.user_message_id)
        if msg is not None:
            self.db.delete(msg)
        session = self.db.get(ChatSession, turn.session_id)
        if session is not None:
            session.hint_level = turn.previous_hint_level
        self.db.commit()

    # --------------------------------------------------------------------------
    # GET /tutor/history/{lesson_id}
    # --------------------------------------------------------------------------
    def get_history(
        self, user: User, lesson_id: int, limit: int
    ) -> tuple[ChatSession | None, list[ChatMessage], int]:
        lesson = self._get_lesson(lesson_id)
        session = self.db.scalar(
            select(ChatSession)
            .where(ChatSession.user_id == user.id, ChatSession.lesson_id == lesson.id)
            .order_by(ChatSession.id.desc())
            .limit(1)
        )
        messages = self._recent_messages(session.id, limit) if session is not None else []
        return session, messages, QuotaGuard(self.db).remaining(user.id)

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _get_lesson(self, lesson_id: int, with_content: bool = False) -> Lesson:
        stmt = (
            select(Lesson)
            .join(Course, Course.id == Lesson.course_id)
            .where(Lesson.id == lesson_id, Course.status == CourseStatus.ACTIVE.value)
        )
        if with_content:
            stmt = stmt.options(selectinload(Lesson.topics), selectinload(Lesson.contents))
        lesson = self.db.scalar(stmt)
        if lesson is None:
            raise LessonNotFoundError("Bài học không tồn tại")
        return lesson

    def _get_or_create_session(self, user_id: int, lesson_id: int, mode: str) -> ChatSession:
        session = self.db.scalar(
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.lesson_id == lesson_id,
                ChatSession.mode == mode,
                ChatSession.status == ChatSessionStatus.ACTIVE.value,
            )
            .order_by(ChatSession.id.desc())
            .limit(1)
        )
        if session is None:
            session = ChatSession(
                user_id=user_id,
                lesson_id=lesson_id,
                mode=mode,
                hint_level=0,
                wrong_streak=0,
                status=ChatSessionStatus.ACTIVE.value,
            )
            self.db.add(session)
            self.db.flush()
        return session

    def _recent_messages(self, session_id: int, limit: int) -> list[ChatMessage]:
        """N tin nhan gan nhat (dung index idx_session_created), tra ve theo thu tu thoi gian tang dan."""
        rows = self.db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        ).all()
        return list(reversed(rows))

    @staticmethod
    def _lesson_context(lesson: Lesson, mode: str, hint_level: int) -> str:
        parts = [f"Bài học: {lesson.title}"]
        if lesson.topics:
            parts.append("Chủ đề: " + ", ".join(t.name for t in lesson.topics))
        if mode == ChatMode.SOCRATIC.value:
            parts.append(
                f"Chế độ: SOCRATIC - bước {hint_level}/{SOCRATIC_MAX_STEPS}. "
                + (
                    "Đây là bước tổng kết, được phép trình bày lời giải."
                    if hint_level >= SOCRATIC_MAX_STEPS
                    else "Chỉ đặt câu hỏi gợi mở, tuyệt đối không đưa đáp án."
                )
            )
        else:
            parts.append("Chế độ: EXPLAIN - giải thích rõ ràng, có ví dụ minh họa.")
        body = "\n\n".join(c.body for c in lesson.contents if c.content_type == "MARKDOWN" and c.body)
        if body:
            parts.append("Nội dung lý thuyết:\n" + body)
        return "\n".join(parts)[:LESSON_CONTEXT_MAX_CHARS]
