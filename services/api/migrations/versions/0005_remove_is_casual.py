from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_remove_is_casual"
down_revision = "0004_auth_and_leaderboard_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("scores")
    }
    if "is_casual" in columns:
        with op.batch_alter_table("scores", recreate="always") as batch_op:
            batch_op.drop_column("is_casual")


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("scores")
    }
    if "is_casual" not in columns:
        with op.batch_alter_table("scores", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_casual", sa.Boolean(), nullable=False, server_default=sa.true()
                )
            )
