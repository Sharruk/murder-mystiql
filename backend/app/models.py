from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


AnswerType = Literal["text", "number", "exact", "case_insensitive"]


@dataclass
class Participant:
    id: str = field(default_factory=lambda: str(uuid4()))
    firebase_uid: str = ""
    email: str = ""
    display_name: str | None = None
    photo_url: str | None = None
    email_verified: bool = True
    is_qualified: bool = False
    created_at: datetime = field(default_factory=now_utc)
    last_login_at: datetime = field(default_factory=now_utc)


@dataclass
class EventConfig:
    wrong_answer_penalty_minutes: int = 5
    wrong_answer_lock_seconds: int = 60
    allow_pause: bool = False
    hint_penalty_default_minutes: int = 2
    max_query_rows: int = 200
    query_timeout_ms: int = 3000
    quiz_required: bool = True
    quiz_qualify_score: int = 3


@dataclass
class Story:
    title: str = "LCU: ECLIPSE"
    prologue: str = "The foundation of the South Indian narcotics corridor rests on three cataclysms: Trichy (2019), Chennai (2022), and Theog (2023)..."
    description: str = "A relational investigation into the ghost shipments and showdown of the LCU Eclipse case."
    disclaimer: str = "LCU: ECLIPSE is fan-made fiction created for entertainment and mystery-game purposes. It is not official canon of the Lokesh Cinematic Universe."


@dataclass
class Event:
    id: str = "e0000000-0000-0000-0000-000000000001"
    slug: str = "invente-2026"
    name: str = "MURDER MYSTIQL: LCU ECLIPSE"
    tagline: str = "Invente 2026 SQL Investigation Challenge"
    description: str = "A high-stakes relational SQL mystery set in the aftermath of the Das & Co collapse."
    status: str = "live"
    config: EventConfig = field(default_factory=EventConfig)
    story: Story = field(default_factory=Story)


@dataclass
class Level:
    id: str
    event_id: str
    level_number: int
    title: str
    narrative_context: str | None = None
    objective: str = ""
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
    description: str | None = None
    visible: bool = True


@dataclass
class Hint:
    id: str
    level_id: str
    title: str
    body: str
    penalty_minutes: int = 2
    repeatable: bool = False
    sort_order: int = 0


@dataclass
class Session:
    id: str
    event_id: str
    team_name: str
    started_at: datetime
    participant_id: str | None = None
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
    quiz_passed: bool = False

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


@dataclass
class QuizQuestion:
    id: str
    prompt: str
    points: int = 1
    options: list[QuizOption] = field(default_factory=list)


@dataclass
class QuizOption:
    id: str
    option_text: str
    is_correct: bool = False


def public_level(level: Level, session: Session | None = None) -> dict[str, Any]:
    completed = session is not None and level.level_number in session.completed_level_numbers
    unlocked = session is None or level.level_number <= session.current_level_number
    return {
        "id": level.id,
        "level_number": level.level_number,
        "title": level.title,
        "narrative_context": level.narrative_context,
        "objective": level.objective,
        "clue": level.clue,
        "answer_type": level.answer_type,
        "active": level.active,
        "unlocked": unlocked,
        "completed": completed,
    }