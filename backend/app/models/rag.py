"""Mô hình CSDL RAG Vector PDF, AI Logs và Quản trị hệ thống.

Phân hệ 7 & 8 (TK-19 / BR-05, BR-09).
Các bảng thực thể:
- documents: Lưu trữ siêu dữ liệu tài liệu giáo trình PDF tải lên (tối đa 20MB theo BR-09).
- document_chunks: Đoạn văn bản sau khi băm nhỏ kèm vector embedding 1536 chiều.
- ai_request_logs: Bản ghi lịch sử gọi AI phục vụ thống kê token và QuotaGuard 50 req/ngày (BR-05).
- prompt_templates: Mẫu system prompt có phiên bản phục vụ A/B testing và cấu hình động.
- system_settings: Cấu hình hệ thống chung (ngưỡng token, quota, tham số AI).
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON, LONGTEXT
from sqlalchemy.types import JSON as GenericJSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AIFeature(str, enum.Enum):
    """Tính năng gọi AI Microservice (SDD Bảng 17)."""
    TUTOR = "TUTOR"
    SOCRATIC = "SOCRATIC"
    QUIZ_GEN = "QUIZ_GEN"
    RAG = "RAG"


class AIProvider(str, enum.Enum):
    """Nhà cung cấp mô hình AI."""
    OPENAI = "openai"
    GEMINI = "gemini"


class Document(Base):
    """Tài liệu giáo trình PDF được tải lên theo từng môn học (SDD Bảng 17 / BR-09)."""
    __tablename__ = "documents"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    course_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False, comment="Kích thước tệp (bytes, tối đa 20MB BR-09)")
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Quan hệ
    course = relationship("Course", back_populates="documents")
    uploader = relationship("User", back_populates="uploaded_documents")
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentChunk.chunk_index",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, course_id={self.course_id}, file_name='{self.file_name}', size={self.file_size})>"


class DocumentChunk(Base):
    """Đoạn văn bản sau khi chia nhỏ kèm vector embedding 1536 chiều (SDD Bảng 17)."""
    __tablename__ = "document_chunks"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    document_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False, comment="Thứ tự của đoạn trong tài liệu")
    page_number = Column(Integer, nullable=False, comment="Số trang gốc trong file PDF để trích nguồn")
    content = Column(Text, nullable=False, comment="Nội dung văn bản đoạn (~500 từ)")
    embedding = Column(
        GenericJSON().with_variant(JSON, "mysql"),
        nullable=True,
        comment="Vector embedding 1536 chiều mảng float phục vụ Cosine Similarity",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Chỉ mục tối ưu hóa truy xuất theo trang gốc (SDD Bảng 18)
    __table_args__ = (
        Index("idx_doc_page", "document_id", "page_number"),
    )

    # Quan hệ N:1
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk={self.chunk_index}, page={self.page_number})>"


class AIRequestLog(Base):
    """Bản ghi log gọi API AI phục vụ thống kê token và cưỡng chế Quota (SDD Bảng 17 & 18)."""
    __tablename__ = "ai_request_logs"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feature = Column(String(30), nullable=False, comment="TUTOR | SOCRATIC | QUIZ_GEN | RAG")
    provider = Column(String(30), nullable=False, comment="openai | gemini")
    tokens_prompt = Column(Integer, default=0, nullable=False, comment="Token đầu vào")
    tokens_completion = Column(Integer, default=0, nullable=False, comment="Token đầu ra")
    latency_ms = Column(Integer, nullable=False, comment="Thời gian phản hồi tính bằng ms")
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Chỉ mục cưỡng chế hạn mức 50 request/ngày (SDD Bảng 18 / BR-05)
    __table_args__ = (
        Index("idx_user_feature_date", "user_id", "feature", "created_at"),
    )

    # Quan hệ N:1
    user = relationship("User", back_populates="ai_request_logs")

    def __repr__(self) -> str:
        return f"<AIRequestLog(id={self.id}, user_id={self.user_id}, feature='{self.feature}', latency={self.latency_ms}ms)>"


class PromptTemplate(Base):
    """Mẫu system prompt quản trị tập trung và hỗ trợ A/B Testing (SDD Bảng 17)."""
    __tablename__ = "prompt_templates"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    code = Column(String(50), nullable=False, index=True, comment="Mã mẫu: TUTOR_EXPLAIN, TUTOR_SOCRATIC, QUIZ_GEN")
    version = Column(Integer, default=1, nullable=False, comment="Phiên bản mẫu phục vụ A/B Testing")
    content = Column(
        Text().with_variant(LONGTEXT, "mysql"),
        nullable=False,
        comment="Nội dung system prompt chứa các tham số biến",
    )
    is_active = Column(Boolean, default=True, nullable=False, comment="Cờ đánh dấu template đang kích hoạt")
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Ràng buộc duy nhất theo mã và phiên bản
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_prompt_code_version"),
    )

    def __repr__(self) -> str:
        return f"<PromptTemplate(id={self.id}, code='{self.code}', v={self.version}, active={self.is_active})>"


class SystemSetting(Base):
    """Cấu hình tham số hệ thống chung (Project_LearnMate_AI.xlsx / Quản trị)."""
    __tablename__ = "system_settings"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    key = Column(String(100), unique=True, nullable=False, index=True, comment="Khóa cấu hình hệ thống")
    value = Column(Text, nullable=False, comment="Giá trị cấu hình (Text hoặc JSON)")
    description = Column(String(255), nullable=True, comment="Mô tả ý nghĩa của cấu hình")
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<SystemSetting(id={self.id}, key='{self.key}')>"
