from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class RunSubmittedResponse(BaseModel):
    status: str = "ok"
    run_id: str
