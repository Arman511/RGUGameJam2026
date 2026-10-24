from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_local_leaderboard"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("leaderboard"):
        op.create_table(
            "leaderboard",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), nullable=False, unique=True),
            sa.Column("timestamp", sa.String(), nullable=False),
            sa.Column("survival_time", sa.Float(), nullable=False),
            sa.Column("final_wave", sa.Integer(), nullable=False),
            sa.Column("enemies_defeated", sa.Integer(), nullable=False),
        )


def downgrade() -> None:
    pass
