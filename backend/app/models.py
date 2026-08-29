from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


AnswerType = Literal["text", "number", "exact", "case_insensitive"]


@dataclass
class EventConfig:
    wrong_answer_penalty_minutes: int = 5
    wrong_answer_lock_seconds: int = 60
    allow_pause: bool = False
    hint_penalty_default_minutes: int = 2


@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid4()))
    slug: str = "murder-mystiql"
    name: str = "MURDER MYSTIQL"
    tagline: str = "A configurable investigation engine"
    description: str = "A story-independent platform for running data-driven investigations."
    status: str = "draft"
    config: EventConfig = field(default_factory=EventConfig)


@dataclass
class Level:
    id: str
    event_id: str
    level_number: int
    title: str
    description: str | None = None
    clue: str | None = None
    answer_type: AnswerType = "case_insensitive"
    answer_values: list[str] = field(default_factory=list)
    active: bool = True


@dataclass
class TableColumn:
    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False


@dataclass
class InvestigationTable:
    name: str
    label: str
    columns: list[TableColumn] = field(default_factory=list)
    unlock_level: int = 1
    visible: bool = True


@dataclass
class Hint:
    id: str
    level_id: str
    title: str
    body: str
    penalty_minutes: int = 2
    repeatable: bool = False


@dataclass
class Session:
    id: str
    event_id: str
    team_name: str
    started_at: datetime
    finish_at: datetime | None = None
    current_level_number: int = 1
    completed_level_numbers: set[int] = field(default_factory=set)
    wrong_submission_count: int = 0
    wrong_penalty_seconds: int = 0
    hint_penalty_seconds: int = 0
    used_hint_ids: set[str] = field(default_factory=set)
    status: str = "IN_PROGRESS"
    last_submission_at: datetime | None = None
    created_at: datetime = field(default_factory=now_utc)

    @property
    def actual_duration_seconds(self) -> int:
        end = self.finish_at or now_utc()
        return max(0, int((end - self.started_at).total_seconds()))

    @property
    def effective_time_seconds(self) -> int:
        return self.actual_duration_seconds + self.wrong_penalty_seconds + self.hint_penalty_seconds


@dataclass
class QueryLog:
    id: str
    session_id: str
    query: str
    success: bool
    row_count: int
    duration_ms: int
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class AnswerSubmission:
    id: str
    session_id: str
    level_id: str
    submitted_answer: str
    correct: bool
    penalty_seconds: int = 0
    lock_seconds: int = 0
    created_at: datetime = field(default_factory=now_utc)


def public_level(level: Level, session: Session | None = None) -> dict[str, Any]:
    completed = session is not None and level.level_number in session.completed_level_numbers
    unlocked = session is None or level.level_number <= session.current_level_number
    return {
        "id": level.id,
        "level_number": level.level_number,
        "title": level.title,
        "description": level.description,
        "clue": level.clue,
        "answer_type": level.answer_type,
        "active": level.active,
        "unlocked": unlocked,
        "completed": completed,
    }