"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_template",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "task_completion",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["task_template.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("template_id", "date", name="uq_completion_template_date"),
    )
    op.create_index("ix_task_completion_template_id", "task_completion", ["template_id"])
    op.create_index("ix_task_completion_date", "task_completion", ["date"])


def downgrade() -> None:
    op.drop_index("ix_task_completion_date", table_name="task_completion")
    op.drop_index("ix_task_completion_template_id", table_name="task_completion")
    op.drop_table("task_completion")
    op.drop_table("task_template")
