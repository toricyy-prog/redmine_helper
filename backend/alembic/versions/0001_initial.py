"""initial

Revision ID: 0001
Revises:
Create Date: 2026-03-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("similar_issues", sa.JSON(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_history_id"), "analysis_history", ["id"], unique=False)
    op.create_index(op.f("ix_analysis_history_issue_id"), "analysis_history", ["issue_id"], unique=False)

    op.create_table(
        "duplicate_detections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_issue_id", sa.Integer(), nullable=False),
        sa.Column("target_issue_id", sa.Integer(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_duplicate_detections_id"), "duplicate_detections", ["id"], unique=False)
    op.create_index(
        op.f("ix_duplicate_detections_source_issue_id"),
        "duplicate_detections",
        ["source_issue_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_duplicate_detections_source_issue_id"), table_name="duplicate_detections")
    op.drop_index(op.f("ix_duplicate_detections_id"), table_name="duplicate_detections")
    op.drop_table("duplicate_detections")
    op.drop_index(op.f("ix_analysis_history_issue_id"), table_name="analysis_history")
    op.drop_index(op.f("ix_analysis_history_id"), table_name="analysis_history")
    op.drop_table("analysis_history")
