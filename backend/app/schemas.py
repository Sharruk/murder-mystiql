from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class AuthVerifyRequest(BaseModel):
    id_token: str = Field(min_length=1)


class ParticipantOut(BaseModel):
    id: str
    firebase_uid: str
    email: str
    display_name: str | None = None
    photo_url: str | None = None
    is_qualified: bool = False


class AuthResponse(BaseModel):
    token: str
    participant: ParticipantOut
    session: dict[str, Any] | None = None


class StartGameRequest(BaseModel):
    team_name: str | None = Field(default=None, max_length=80)


class QueryRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=12000)


class AnswerRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=500)


class HintRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    hint_id: str = Field(min_length=1, max_length=100)


class FinishRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)


class QuizSubmitRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    answers: dict[str, str] = Field(default_factory=dict)