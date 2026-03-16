"""fix_settings_enable_auto_comment_boolean

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite는 컬럼 타입 변경을 직접 지원하지 않으므로 테이블 재생성
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.alter_column(
            "enable_auto_comment",
            new_column_name="enable_auto_comment",
            existing_type=sa.String(length=10),
            type_=sa.Boolean(),
            existing_nullable=True,
            postgresql_using="enable_auto_comment::boolean",
        )


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.alter_column(
            "enable_auto_comment",
            new_column_name="enable_auto_comment",
            existing_type=sa.Boolean(),
            type_=sa.String(length=10),
            existing_nullable=True,
        )
