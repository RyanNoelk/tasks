"""one_off_task table

Revision ID: 0002_one_off_task
Revises: 0001_initial
Create Date: 2026-05-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_one_off_task"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "one_off_task",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_one_off_completed_at", "one_off_task", ["completed_at"])


def downgrade() -> None:
    op.drop_index("ix_one_off_completed_at", table_name="one_off_task")
    op.drop_table("one_off_task")
