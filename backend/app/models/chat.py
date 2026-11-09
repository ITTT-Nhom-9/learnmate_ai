import enum
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChatMode(str, enum.Enum):
    EXPLAIN = "EXPLAIN"
    SOCRATIC = "SOCRATIC"


class ChatRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class ChatSessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    lesson_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    mode = Column(
        String(20),
        nullable=False,
        default=ChatMode.EXPLAIN.value
    )
    hint_level = Column(
        Integer,
        nullable=False,
        default=0
    )
    wrong_streak = Column(
        Integer,
        nullable=False,
        default=0
    )
    status = Column(
        String(20),
        nullable=False,
        default=ChatSessionStatus.ACTIVE.value
    )

    # Quan hệ N:1
    user = relationship("User", back_populates="chat_sessions")
    lesson = relationship("Lesson", back_populates="chat_sessions")

    # Quan hệ 1:N với ChatMessage
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.created_at"
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, lesson_id={self.lesson_id}, mode='{self.mode}')>"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    session_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(
        String(20),
        nullable=False
    )
    content = Column(
        Text,
        nullable=False
    )
    tokens_used = Column(
        Integer,
        nullable=False,
        default=0
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Tối ưu hóa truy vấn 10 tin nhắn gần nhất ráp ngữ cảnh (Theo Bảng 18: idx_session_created)
    __table_args__ = (
        Index("idx_session_created", "session_id", "created_at"),
    )

    # Quan hệ N:1 với ChatSession
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}')>"

