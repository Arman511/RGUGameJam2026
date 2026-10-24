from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_rank_runs_without_score"
down_revision = "0002_survival_and_wave"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scores", recreate="always") as batch_op:
        batch_op.drop_column("score")
        batch_op.drop_column("survival_time")
        batch_op.drop_column("final_wave")


def downgrade() -> None:
    with op.batch_alter_table("scores", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("survival_time", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("final_wave", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("score", sa.Integer(), nullable=False, server_default="0")
        )
    op.execute(
        "UPDATE scores SET survival_time = time_survived, final_wave = wave_number"
    )
