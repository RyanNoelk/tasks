"""one_off_task.due_date

Revision ID: 0004_one_off_due_date
Revises: 0003_schedule
Create Date: 2026-05-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_one_off_due_date"
down_revision: Union[str, None] = "0003_schedule"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("one_off_task") as batch:
        batch.add_column(sa.Column("due_date", sa.Date(), nullable=True))
    op.create_index("ix_one_off_due_date", "one_off_task", ["due_date"])


def downgrade() -> None:
    op.drop_index("ix_one_off_due_date", table_name="one_off_task")
    with op.batch_alter_table("one_off_task") as batch:
        batch.drop_column("due_date")
