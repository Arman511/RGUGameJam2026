from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def require_password_complexity(cls, value: str) -> str:
        requirements = (
            (any(character.isupper() for character in value), "an uppercase letter"),
            (any(character.islower() for character in value), "a lowercase letter"),
            (any(character.isdigit() for character in value), "a number"),
            (
                any(
                    not character.isalnum() and not character.isspace()
                    for character in value
                ),
                "a symbol",
            ),
        )
        missing = [
            description for satisfied, description in requirements if not satisfied
        ]
        if missing:
            raise ValueError("Password must include " + ", ".join(missing) + ".")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    expires_at: datetime


class RegisterResponse(BaseModel):
    user: UserResponse
    message: str


class MessageResponse(BaseModel):
    message: str


class RunSubmit(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    time_survived: float = Field(ge=0, le=86_400)
    wave_number: int = Field(ge=0, le=1_000)
    enemies_defeated: int = Field(ge=0, le=100_000)


class RunResponse(BaseModel):
    run_id: str
    username: str
    time_survived: float
    wave_number: int
    enemies_defeated: int
    submitted_at: datetime


class LeaderboardResponse(BaseModel):
    scores: list[RunResponse]
    total: int
    offset: int
    limit: int


class LeaderboardFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Literal[
        "last_hour",
        "last_day",
        "last_week",
        "last_month",
        "last_year",
        "custom",
        "all_time",
    ] = "all_time"
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_custom_dates(self) -> "LeaderboardFilters":
        if self.period != "custom":
            if self.start_date is not None or self.end_date is not None:
                raise ValueError("Custom dates can only be used with the custom period.")
            return self

        if self.start_date is None or self.end_date is None:
            raise ValueError("Custom period requires both start_date and end_date.")
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date.")
        if self.end_date > datetime.now(UTC).date():
            raise ValueError("end_date cannot be in the future.")
        return self


class RunSubmittedResponse(BaseModel):
    status: str = "ok"
    run_id: str
