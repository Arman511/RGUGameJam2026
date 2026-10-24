from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_remove_local_score"
down_revision = "0001_local_leaderboard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("leaderboard")
    }
    if "score" in columns:
        with op.batch_alter_table("leaderboard", recreate="always") as batch_op:
            batch_op.drop_column("score")


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("leaderboard")
    }
    if "score" not in columns:
        with op.batch_alter_table("leaderboard") as batch_op:
            batch_op.add_column(
                sa.Column("score", sa.Integer(), nullable=False, server_default="0")
            )
