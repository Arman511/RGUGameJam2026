from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_player_selection"
down_revision = "0005_game_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("player_settings"):
        op.create_table(
            "player_settings",
            sa.Column("setting_key", sa.String(), primary_key=True),
            sa.Column("player_number", sa.Integer(), nullable=False),
            sa.CheckConstraint(
                "player_number BETWEEN 1 AND 6",
                name="ck_player_settings_number_range",
            ),
        )
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO player_settings(setting_key, player_number)
            VALUES ('player_number', 1)
            ON CONFLICT(setting_key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("player_settings"):
        op.drop_table("player_settings")
