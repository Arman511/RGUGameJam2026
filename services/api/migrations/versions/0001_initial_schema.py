from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("username", sa.String(length=32), nullable=False, unique=True),
            sa.Column(
                "normalized_username", sa.String(length=32), nullable=False, unique=True
            ),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
        )
    if not inspector.has_table("auth_tokens"):
        op.create_table(
            "auth_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
        )
    if not inspector.has_table("scores"):
        op.create_table(
            "scores",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("run_id", sa.String(length=128), nullable=False),
            sa.Column("survival_time", sa.Float(), nullable=False),
            sa.Column("final_wave", sa.Integer(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("enemies_defeated", sa.Integer(), nullable=False),
            sa.Column(
                "submitted_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.Column(
                "is_casual", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.UniqueConstraint("user_id", "run_id", name="uq_scores_user_run"),
        )


def downgrade() -> None:
    pass
