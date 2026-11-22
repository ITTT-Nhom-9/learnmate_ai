"""Add the recommendation priority index.

Revision ID: 005_recommendation_index
Revises: 004_add_progress_rag_admin_tables
"""

from alembic import op


revision = "005_recommendation_index"
down_revision = "004_add_progress_rag_admin_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_user_status_prio", "recommendations", ["user_id", "status", "priority"]
    )


def downgrade() -> None:
    op.drop_index("idx_user_status_prio", table_name="recommendations")
