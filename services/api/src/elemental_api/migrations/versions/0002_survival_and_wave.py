from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_survival_and_wave"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("scores")
    }
    if "time_survived" not in columns:
        op.add_column(
            "scores",
            sa.Column("time_survived", sa.Float(), nullable=False, server_default="0"),
        )
        if "survival_time" in columns:
            op.execute("UPDATE scores SET time_survived = survival_time")
    if "wave_number" not in columns:
        op.add_column(
            "scores",
            sa.Column("wave_number", sa.Integer(), nullable=False, server_default="0"),
        )
        if "final_wave" in columns:
            op.execute("UPDATE scores SET wave_number = final_wave")


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("scores")
    }
    if "wave_number" in columns:
        op.drop_column("scores", "wave_number")
    if "time_survived" in columns:
        op.drop_column("scores", "time_survived")
