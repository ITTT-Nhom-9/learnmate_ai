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
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class CourseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ContentType(str, enum.Enum):
    MARKDOWN = "MARKDOWN"
    VIDEO = "VIDEO"
    PDF = "PDF"


class Course(Base):
    __tablename__ = "courses"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    code = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default=CourseStatus.ACTIVE.value
    )

    # Quan hệ 1:N với Enrollment
    enrollments = relationship(
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    # Quan hệ 1:N với Lesson
    lessons = relationship(
        "Lesson",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Lesson.order_index"
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, code='{self.code}', title='{self.title}')>"


class Enrollment(Base):
    __tablename__ = "enrollments"

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
    course_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    enrolled_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Ràng buộc UNIQUE cặp (user_id, course_id)
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_user_course"),
    )

    # Quan hệ N:1
    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment(id={self.id}, user_id={self.user_id}, course_id={self.course_id})>"


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    course_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(200), nullable=False)
    order_index = Column(Integer, nullable=False, default=1)

    # Quan hệ N:1 với Course
    course = relationship("Course", back_populates="lessons")

    # Quan hệ 1:N với Topic
    topics = relationship(
        "Topic",
        back_populates="lesson",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    # Quan hệ 1:N với LessonContent
    contents = relationship(
        "LessonContent",
        back_populates="lesson",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, course_id={self.course_id}, title='{self.title}')>"


class Topic(Base):
    __tablename__ = "topics"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    lesson_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Quan hệ N:1 với Lesson
    lesson = relationship("Lesson", back_populates="topics")

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, lesson_id={self.lesson_id}, name='{self.name}')>"


class LessonContent(Base):
    __tablename__ = "lesson_contents"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    lesson_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content_type = Column(
        String(30),
        nullable=False,
        default=ContentType.MARKDOWN.value
    )
    body = Column(Text, nullable=False)

    # Quan hệ N:1 với Lesson
    lesson = relationship("Lesson", back_populates="contents")

    def __repr__(self) -> str:
        return f"<LessonContent(id={self.id}, lesson_id={self.lesson_id}, content_type='{self.content_type}')>"
