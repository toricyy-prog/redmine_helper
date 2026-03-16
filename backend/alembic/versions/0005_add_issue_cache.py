"""add_issue_cache

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "issue_cache",
        sa.Column("issue_id", sa.Integer(), primary_key=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("journals", sa.JSON(), nullable=True),
        sa.Column("cached_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("issue_cache")
