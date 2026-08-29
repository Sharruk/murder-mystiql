from typing import Any
from pydantic import BaseModel, Field


class StartGameRequest(BaseModel):
    team_name: str = Field(min_length=1, max_length=80)


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


class ApiError(BaseModel):
    detail: dict[str, Any]