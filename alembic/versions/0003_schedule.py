"""task_template schedule (rrule + dtstart)

Revision ID: 0003_schedule
Revises: 0002_one_off_task
Create Date: 2026-05-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_schedule"
down_revision: Union[str, None] = "0002_one_off_task"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("task_template") as batch:
        batch.add_column(
            sa.Column(
                "schedule_rrule",
                sa.String(),
                nullable=False,
                server_default="FREQ=DAILY",
            )
        )
        batch.add_column(sa.Column("schedule_dtstart", sa.Date(), nullable=True))

    op.execute("UPDATE task_template SET schedule_dtstart = DATE(created_at)")

    with op.batch_alter_table("task_template") as batch:
        batch.alter_column("schedule_dtstart", existing_type=sa.Date(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("task_template") as batch:
        batch.drop_column("schedule_dtstart")
        batch.drop_column("schedule_rrule")
