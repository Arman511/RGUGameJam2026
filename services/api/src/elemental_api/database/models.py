from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    normalized_username: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    auth_tokens: Mapped[list[AuthToken]] = relationship(back_populates="user")
    runs: Mapped[list[RunRecord]] = relationship(back_populates="user")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="auth_tokens")


class RunRecord(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("user_id", "run_id", name="uq_scores_user_run"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    time_survived: Mapped[float] = mapped_column(nullable=False)
    wave_number: Mapped[int] = mapped_column(Integer, nullable=False)
    enemies_defeated: Mapped[int] = mapped_column(Integer, nullable=False)
    is_casual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    user: Mapped[User] = relationship(back_populates="runs")
