from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_leaderboard_rank_index"
down_revision = "0002_remove_local_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    indexes = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("leaderboard")
    }
    if "ix_leaderboard_rank" not in indexes:
        op.create_index(
            "ix_leaderboard_rank",
            "leaderboard",
            ["survival_time", "enemies_defeated", "final_wave"],
        )


def downgrade() -> None:
    indexes = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("leaderboard")
    }
    if "ix_leaderboard_rank" in indexes:
        op.drop_index("ix_leaderboard_rank", table_name="leaderboard")
