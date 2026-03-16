"""add_category_and_comment_fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analysis_history", sa.Column("category", sa.String(length=100), nullable=True))
    op.add_column("analysis_history", sa.Column("category_confidence", sa.Float(), nullable=True))
    op.add_column("analysis_history", sa.Column("comment_written", sa.Integer(), nullable=True, server_default="0"))


def downgrade() -> None:
    op.drop_column("analysis_history", "comment_written")
    op.drop_column("analysis_history", "category_confidence")
    op.drop_column("analysis_history", "category")
