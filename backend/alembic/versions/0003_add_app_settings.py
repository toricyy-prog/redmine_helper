"""add_app_settings

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("similarity_threshold", sa.Float(), nullable=True, server_default="0.3"),
        sa.Column("duplicate_threshold", sa.Float(), nullable=True, server_default="0.9"),
        sa.Column("max_similar_issues", sa.Integer(), nullable=True, server_default="5"),
        sa.Column("category_list", sa.Text(), nullable=True, server_default=""),
        sa.Column("enable_auto_comment", sa.String(length=10), nullable=True, server_default="false"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
