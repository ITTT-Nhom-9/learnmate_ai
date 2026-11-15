"""003_add_is_correct_to_attempt_answers

Lưu kết quả đúng/sai của từng câu trong lịch sử làm bài (BR-08).

Revision ID: 003_add_is_correct_to_attempt_answers
Revises: 002_add_chat_and_quiz_tables
Create Date: 2026-11-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "003_add_is_correct_to_attempt_answers"
down_revision: Union[str, None] = "002_add_chat_and_quiz_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attempt_answers",
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("attempt_answers", "is_correct")
