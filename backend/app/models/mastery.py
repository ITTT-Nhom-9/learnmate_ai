"""Mô hình CSDL Theo dõi tiến độ học tập và độ thông thạo kiến thức (Mastery).

Phân hệ 6 (TK-19 / BR-08, UC-07).
Các bảng thực thể:
- topic_mastery (user_topic_mastery): Điểm thành thạo EMA (0.00% - 100.00%) theo từng chủ đề.
- recommendations: Đề xuất ôn tập cá nhân hóa dựa trên lỗ hổng kiến thức.
- learning_events (student_activity_logs): Nhật ký sự kiện hành vi học tập của sinh viên.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.types import JSON as GenericJSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class MasteryStatus(str, enum.Enum):
    """Phân hạng năng lực thông thạo chủ đề kiến thức (SDD Bảng 16 / BR-08)."""
    WEAK = "WEAK"        # Dưới 60%: Điểm yếu cần bổ túc
    FAIR = "FAIR"        # 60% - 79%: Nắm mức khá
    MASTER = "MASTER"    # Từ 80% trở lên: Đã thành thạo chuyên sâu


# Bí danh tương thích 100% với mã nguồn mẫu trong SDD Bảng 7
TopicStatusEnum = MasteryStatus


class RecommendationAction(str, enum.Enum):
    """Loại hành động khuyến nghị ôn tập (SDD Bảng 16)."""
    REVIEW_THEORY = "REVIEW_THEORY"    # Đọc lại nội dung lý thuyết
    SOCRATIC_CHAT = "SOCRATIC_CHAT"    # Hỏi đáp gợi mở với Gia sư Socratic
    RETAKE_QUIZ = "RETAKE_QUIZ"        # Làm bài kiểm tra thích ứng mới


class RecommendationStatus(str, enum.Enum):
    """Trạng thái khuyến nghị ôn tập."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class LearningEventType(str, enum.Enum):
    """Phân loại sự kiện hành vi học tập."""
    LOGIN = "LOGIN"
    CHAT_TUTOR = "CHAT_TUTOR"
    SUBMIT_QUIZ = "SUBMIT_QUIZ"
    VIEW_LESSON = "VIEW_LESSON"


class TopicMastery(Base):
    """Độ thành thạo kiến thức theo từng chủ đề (SDD Bảng 16 / Excel user_topic_mastery)."""
    __tablename__ = "topic_mastery"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mastery_score = Column(
        Numeric(5, 2),
        nullable=False,
        default=0.00,
        comment="Điểm thành thạo EMA từ 0.00% đến 100.00%",
    )
    status = Column(
        String(20),
        nullable=False,
        default=MasteryStatus.WEAK.value,
        comment="Phân hạng: WEAK (<60), FAIR (60-79), MASTER (>=80)",
    )
    last_practiced_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Thời điểm làm bài trắc nghiệm gần nhất",
    )

    # Ràng buộc toàn vẹn & Chỉ mục tối ưu hóa (SDD Bảng 16 & 18)
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_mastery"),
        Index("idx_user_topic_mastery", "user_id", "status", "mastery_score"),
    )

    # Quan hệ N:1
    user = relationship("User", back_populates="topic_masteries")
    topic = relationship("Topic", back_populates="masteries")

    def __repr__(self) -> str:
        return f"<TopicMastery(id={self.id}, user_id={self.user_id}, topic_id={self.topic_id}, score={self.mastery_score}, status='{self.status}')>"


# Bí danh tương thích ngược và khớp 100% với file Project_LearnMate_AI.xlsx
UserTopicMastery = TopicMastery


class Recommendation(Base):
    """Nhiệm vụ gợi ý ôn tập cá nhân hóa cho sinh viên (SDD Bảng 16)."""
    __tablename__ = "recommendations"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(
        String(30),
        nullable=False,
        default=RecommendationAction.REVIEW_THEORY.value,
        comment="REVIEW_THEORY | SOCRATIC_CHAT | RETAKE_QUIZ",
    )
    priority = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Mức ưu tiên ôn tập (1: Cao nhất, 5: Thấp)",
    )
    status = Column(
        String(20),
        nullable=False,
        default=RecommendationStatus.PENDING.value,
        comment="PENDING | COMPLETED",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Quan hệ N:1
    user = relationship("User", back_populates="recommendations")
    topic = relationship("Topic", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation(id={self.id}, user_id={self.user_id}, topic_id={self.topic_id}, action='{self.action_type}', priority={self.priority})>"


class LearningEvent(Base):
    """Nhật ký sự kiện hành vi học tập (SDD Bảng 16 / Excel student_activity_logs)."""
    __tablename__ = "learning_events"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(
        String(50),
        nullable=False,
        comment="LOGIN | CHAT_TUTOR | SUBMIT_QUIZ | VIEW_LESSON",
    )
    event_data = Column(
        GenericJSON().with_variant(JSON, "mysql"),
        nullable=True,
        comment="Dữ liệu chi tiết sự kiện phân tích hành vi",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Quan hệ N:1
    user = relationship("User", back_populates="learning_events")
    topic = relationship("Topic", back_populates="learning_events")

    def __repr__(self) -> str:
        return f"<LearningEvent(id={self.id}, user_id={self.user_id}, event_type='{self.event_type}')>"


# Bí danh tương thích 100% với tên gọi trong Project_LearnMate_AI.xlsx
StudentActivityLog = LearningEvent
