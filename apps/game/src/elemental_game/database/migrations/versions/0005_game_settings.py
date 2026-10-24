from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_game_settings"
down_revision = "0004_local_leaderboard_username"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("game_settings"):
        op.create_table(
            "game_settings",
            sa.Column("setting_key", sa.String(), primary_key=True),
            sa.Column(
                "setting_value",
                sa.Float(),
                nullable=False,
                server_default="1.0",
            ),
            sa.CheckConstraint(
                "setting_value >= 0.0 AND setting_value <= 1.0",
                name="ck_game_settings_volume_range",
            ),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("game_settings"):
        op.drop_table("game_settings")
