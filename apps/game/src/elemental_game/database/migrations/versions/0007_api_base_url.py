from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_api_base_url"
down_revision = "0006_player_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("game_text_settings"):
        op.create_table(
            "game_text_settings",
            sa.Column("setting_key", sa.String(), primary_key=True),
            sa.Column("setting_value", sa.String(255), nullable=False),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("game_text_settings"):
        op.drop_table("game_text_settings")
