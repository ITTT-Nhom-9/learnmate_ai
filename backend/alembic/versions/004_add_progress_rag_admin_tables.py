"""004_add_progress_rag_admin_tables

Thiết lập 7 bảng CSDL Theo dõi tiến độ (Mastery), RAG Vector PDF và Quản trị hệ thống (TK-19 / Phân hệ 6, 7, 8).
Các bảng:
1. topic_mastery (user_topic_mastery)
2. recommendations
3. learning_events (student_activity_logs)
4. documents
5. document_chunks
6. ai_request_logs
7. prompt_templates
8. system_settings

Revision ID: 004_add_progress_rag_admin_tables
Revises: 003_add_is_correct_to_attempt_answers
Create Date: 2026-11-16 14:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "004_add_progress_rag_admin_tables"
down_revision: Union[str, None] = "003_add_is_correct_to_attempt_answers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. topic_mastery (SDD Bảng 16 / Excel user_topic_mastery)
    op.create_table(
        "topic_mastery",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("mastery_score", sa.Numeric(precision=5, scale=2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="WEAK", nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_user_topic_mastery"),
    )
    op.create_index(op.f("ix_topic_mastery_id"), "topic_mastery", ["id"], unique=False)
    op.create_index(op.f("ix_topic_mastery_user_id"), "topic_mastery", ["user_id"], unique=False)
    op.create_index(op.f("ix_topic_mastery_topic_id"), "topic_mastery", ["topic_id"], unique=False)
    op.create_index("idx_user_topic_mastery", "topic_mastery", ["user_id", "status", "mastery_score"], unique=False)

    # 2. recommendations (SDD Bảng 16)
    op.create_table(
        "recommendations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", sa.String(length=30), server_default="REVIEW_THEORY", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendations_id"), "recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_recommendations_user_id"), "recommendations", ["user_id"], unique=False)
    op.create_index(op.f("ix_recommendations_topic_id"), "recommendations", ["topic_id"], unique=False)

    # 3. learning_events (SDD Bảng 16 / Excel student_activity_logs)
    op.create_table(
        "learning_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_events_id"), "learning_events", ["id"], unique=False)
    op.create_index(op.f("ix_learning_events_user_id"), "learning_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_learning_events_topic_id"), "learning_events", ["topic_id"], unique=False)

    # 4. documents (SDD Bảng 17 / BR-09)
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
    op.create_index(op.f("ix_documents_course_id"), "documents", ["course_id"], unique=False)
    op.create_index(op.f("ix_documents_uploaded_by"), "documents", ["uploaded_by"], unique=False)

    # 5. document_chunks (SDD Bảng 17 & 18)
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_chunks_id"), "document_chunks", ["id"], unique=False)
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)
    op.create_index("idx_doc_page", "document_chunks", ["document_id", "page_number"], unique=False)

    # 6. ai_request_logs (SDD Bảng 17 & 18 / BR-05)
    op.create_table(
        "ai_request_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("feature", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("tokens_prompt", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_completion", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_request_logs_id"), "ai_request_logs", ["id"], unique=False)
    op.create_index(op.f("ix_ai_request_logs_user_id"), "ai_request_logs", ["user_id"], unique=False)
    op.create_index("idx_user_feature_date", "ai_request_logs", ["user_id", "feature", "created_at"], unique=False)

    # 7. prompt_templates (SDD Bảng 17)
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("content", sa.Text().with_variant(mysql.LONGTEXT, "mysql"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_prompt_code_version"),
    )
    op.create_index(op.f("ix_prompt_templates_id"), "prompt_templates", ["id"], unique=False)
    op.create_index(op.f("ix_prompt_templates_code"), "prompt_templates", ["code"], unique=False)

    # 8. system_settings (Excel / Quản trị)
    op.create_table(
        "system_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_system_settings_key"),
    )
    op.create_index(op.f("ix_system_settings_id"), "system_settings", ["id"], unique=False)
    op.create_index(op.f("ix_system_settings_key"), "system_settings", ["key"], unique=True)


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("prompt_templates")
    op.drop_table("ai_request_logs")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("learning_events")
    op.drop_table("recommendations")
    op.drop_table("topic_mastery")
