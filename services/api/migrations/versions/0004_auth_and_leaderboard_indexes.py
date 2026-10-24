from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_auth_and_leaderboard_indexes"
down_revision = "0003_rank_runs_without_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    indexes = {
        table: {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
        for table in ("auth_tokens", "scores")
    }
    for name, columns in (
        ("ix_auth_tokens_user_id", ["user_id"]),
        ("ix_auth_tokens_expires_at", ["expires_at"]),
        ("ix_auth_tokens_revoked_at", ["revoked_at"]),
    ):
        if name not in indexes["auth_tokens"]:
            op.create_index(name, "auth_tokens", columns)
    if "ix_scores_leaderboard_rank" not in indexes["scores"]:
        op.create_index(
            "ix_scores_leaderboard_rank",
            "scores",
            ["time_survived", "enemies_defeated", "wave_number", "submitted_at"],
        )


def downgrade() -> None:
    for name, table in (
        ("ix_scores_leaderboard_rank", "scores"),
        ("ix_auth_tokens_revoked_at", "auth_tokens"),
        ("ix_auth_tokens_expires_at", "auth_tokens"),
        ("ix_auth_tokens_user_id", "auth_tokens"),
    ):
        indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
        if name in indexes:
            op.drop_index(name, table_name=table)
