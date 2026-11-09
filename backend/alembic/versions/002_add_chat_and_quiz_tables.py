"""002_add_chat_and_quiz_tables

Revision ID: 002_add_chat_and_quiz_tables
Revises: 001_initial_7_tables
Create Date: 2026-11-09 18:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_chat_and_quiz_tables"
down_revision: Union[str, None] = "001_initial_7_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. chat_sessions
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(length=20), server_default="EXPLAIN", nullable=False),
        sa.Column("hint_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("wrong_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_chat_sessions_id"), "chat_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_lesson_id"), "chat_sessions", ["lesson_id"], unique=False)

    # 2. chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_chat_messages_id"), "chat_messages", ["id"], unique=False)
    op.create_index(op.f("ix_chat_messages_session_id"), "chat_messages", ["session_id"], unique=False)
    op.create_index("idx_session_created", "chat_messages", ["session_id", "created_at"], unique=False)

    # 3. quizzes
    op.create_table(
        "quizzes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("total_questions", sa.Integer(), server_default="5", nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_quizzes_id"), "quizzes", ["id"], unique=False)
    op.create_index(op.f("ix_quizzes_topic_id"), "quizzes", ["topic_id"], unique=False)

    # 4. questions
    op.create_table(
        "questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quiz_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_questions_id"), "questions", ["id"], unique=False)
    op.create_index(op.f("ix_questions_quiz_id"), "questions", ["quiz_id"], unique=False)

    # 5. question_options
    op.create_table(
        "question_options",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("opt_label", sa.String(length=1), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_question_options_id"), "question_options", ["id"], unique=False)
    op.create_index(op.f("ix_question_options_question_id"), "question_options", ["question_id"], unique=False)

    # 6. quiz_attempts
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quiz_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="SUBMITTED", nullable=False),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_quiz_attempts_id"), "quiz_attempts", ["id"], unique=False)
    op.create_index(op.f("ix_quiz_attempts_quiz_id"), "quiz_attempts", ["quiz_id"], unique=False)
    op.create_index(op.f("ix_quiz_attempts_user_id"), "quiz_attempts", ["user_id"], unique=False)

    # 7. attempt_answers
    op.create_table(
        "attempt_answers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("selected_option_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["quiz_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_option_id"], ["question_options.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_attempt_answers_id"), "attempt_answers", ["id"], unique=False)
    op.create_index(op.f("ix_attempt_answers_attempt_id"), "attempt_answers", ["attempt_id"], unique=False)
    op.create_index(op.f("ix_attempt_answers_question_id"), "attempt_answers", ["question_id"], unique=False)
    op.create_index(op.f("ix_attempt_answers_selected_option_id"), "attempt_answers", ["selected_option_id"], unique=False)


def downgrade() -> None:
    op.drop_table("attempt_answers")
    op.drop_table("quiz_attempts")
    op.drop_table("question_options")
    op.drop_table("questions")
    op.drop_table("quizzes")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")

