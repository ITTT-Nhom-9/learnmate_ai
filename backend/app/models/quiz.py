import enum
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class QuizDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuizAttemptStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    topic_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(200), nullable=False)
    difficulty = Column(
        String(20),
        nullable=False
    )
    total_questions = Column(
        Integer,
        nullable=False,
        default=5
    )

    # Quan hệ N:1 với Topic
    topic = relationship("Topic", back_populates="quizzes")

    # Quan hệ 1:N với Question
    questions = relationship(
        "Question",
        back_populates="quiz",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Question.id"
    )

    # Quan hệ 1:N với QuizAttempt
    attempts = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="QuizAttempt.id"
    )

    def __repr__(self) -> str:
        return f"<Quiz(id={self.id}, topic_id={self.topic_id}, title='{self.title}', difficulty='{self.difficulty}')>"


class Question(Base):
    __tablename__ = "questions"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    quiz_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)

    # Quan hệ N:1 với Quiz
    quiz = relationship("Quiz", back_populates="questions")

    # Quan hệ 1:N với QuestionOption
    options = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="QuestionOption.id"
    )

    # Quan hệ 1:N với AttemptAnswer
    attempt_answers = relationship(
        "AttemptAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, quiz_id={self.quiz_id})>"


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    question_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    opt_label = Column(String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    content = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)

    # Quan hệ N:1 với Question
    question = relationship("Question", back_populates="options")

    def __repr__(self) -> str:
        return f"<QuestionOption(id={self.id}, question_id={self.question_id}, opt_label='{self.opt_label}')>"


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    quiz_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    score = Column(
        Numeric(5, 2),
        nullable=False
    )
    duration_sec = Column(
        Integer,
        nullable=False
    )
    status = Column(
        String(20),
        nullable=False,
        default=QuizAttemptStatus.SUBMITTED.value
    )

    # Quan hệ N:1
    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User", back_populates="quiz_attempts")

    # Quan hệ 1:N với AttemptAnswer
    answers = relationship(
        "AttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AttemptAnswer.id"
    )

    def __repr__(self) -> str:
        return f"<QuizAttempt(id={self.id}, quiz_id={self.quiz_id}, user_id={self.user_id}, score={self.score})>"


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    attempt_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    selected_option_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("question_options.id"),
        nullable=True,
        index=True
    )

    # Quan hệ N:1
    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question", back_populates="attempt_answers")
    selected_option = relationship("QuestionOption")

    def __repr__(self) -> str:
        return f"<AttemptAnswer(id={self.id}, attempt_id={self.attempt_id}, question_id={self.question_id})>"

