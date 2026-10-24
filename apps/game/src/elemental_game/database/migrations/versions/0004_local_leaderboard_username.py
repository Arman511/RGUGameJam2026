from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_local_leaderboard_username"
down_revision = "0003_leaderboard_rank_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("leaderboard")
    }
    if "username" not in columns:
        with op.batch_alter_table("leaderboard") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "username",
                    sa.String(),
                    nullable=False,
                    server_default="Guest",
                )
            )


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("leaderboard")
    }
    if "username" in columns:
        with op.batch_alter_table("leaderboard") as batch_op:
            batch_op.drop_column("username")
