from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(RegisterRequest):
    pass


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    expires_at: datetime


class MessageResponse(BaseModel):
    message: str


class RegisterResponse(MessageResponse):
    user: UserResponse


class LocalRunRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    run_id: str = Field(min_length=1, max_length=128)
    survival_time: float = Field(ge=0, le=86_400)
    final_wave: int = Field(ge=0, le=1_000)
    enemies_defeated: int = Field(ge=0, le=100_000)

    def to_submission(self) -> RunSubmission:
        return RunSubmission(
            run_id=self.run_id,
            time_survived=self.survival_time,
            wave_number=self.final_wave,
            enemies_defeated=self.enemies_defeated,
        )


class RunSubmission(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    time_survived: float = Field(ge=0, le=86_400)
    wave_number: int = Field(ge=0, le=1_000)
    enemies_defeated: int = Field(ge=0, le=100_000)


class RunSubmittedResponse(BaseModel):
    status: str
    run_id: str


class MatchConfigResponse(BaseModel):
    join_timeout_seconds: float = Field(gt=0)


class LeaderboardEntry(BaseModel):
    run_id: str
    username: str
    time_survived: float
    wave_number: int
    enemies_defeated: int
    submitted_at: datetime


class LeaderboardResponse(BaseModel):
    scores: list[LeaderboardEntry]
