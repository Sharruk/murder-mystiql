from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from .models import (
    AnswerSubmission,
    Event,
    Hint,
    InvestigationTable,
    Level,
    QueryLog,
    Session,
    TableColumn,
    now_utc,
)


class GameError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "game_error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    duration_ms: int


class GameStore:
    """Runtime repository with an in-memory adapter for empty local installs.

    The relational schema in database/schema.sql is the production persistence contract.
    Keeping this adapter behind a store boundary lets an authenticated repository be added
    later without moving game rules into the React client.
    """

    def __init__(self) -> None:
        self.event = Event()
        self.levels: list[Level] = []
        self.tables: list[InvestigationTable] = []
        self.hints: list[Hint] = []
        self.sessions: dict[str, Session] = {}
        self.query_logs: list[QueryLog] = []
        self.answer_submissions: list[AnswerSubmission] = []
        self._lock = asyncio.Lock()

    async def start_session(self, team_name: str) -> Session:
        cleaned = " ".join(team_name.split()).strip()
        if not cleaned:
            raise GameError("Enter a team name to begin.", 422, "team_name_required")
        if len(cleaned) > 80:
            raise GameError("Team name must be 80 characters or fewer.", 422, "team_name_too_long")
        async with self._lock:
            session_id = str(uuid4())
            session = Session(
                id=session_id,
                event_id=self.event.id,
                team_name=cleaned,
                started_at=now_utc(),
                current_level_number=1 if self.levels else 0,
            )
            self.sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)
        if not session:
            raise GameError("This investigation session could not be found.", 404, "session_not_found")
        return session

    def get_level_for_session(self, session: Session, level_id: str | None = None) -> Level | None:
        if level_id:
            level = next((item for item in self.levels if item.id == level_id), None)
        else:
            level = next((item for item in self.levels if item.level_number == session.current_level_number), None)
        if level and level.level_number > session.current_level_number:
            raise GameError("That level is still locked.", 403, "level_locked")
        return level

    def public_state(self, session: Session) -> dict[str, Any]:
        active_levels = [level for level in self.levels if level.active]
        current_level = self.get_level_for_session(session)
        lock_remaining = 0
        if session.last_submission_at:
            elapsed = (now_utc() - session.last_submission_at).total_seconds()
            lock_remaining = max(0, self.event.config.wrong_answer_lock_seconds - int(elapsed))
        return {
            "session_id": session.id,
            "event": {
                "name": self.event.name,
                "slug": self.event.slug,
                "tagline": self.event.tagline,
                "description": self.event.description,
                "status": self.event.status,
            },
            "team_name": session.team_name,
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "finish_at": session.finish_at.isoformat() if session.finish_at else None,
            "current_level_number": session.current_level_number,
            "total_levels": len(active_levels),
            "completed_levels": len(session.completed_level_numbers),
            "actual_duration_seconds": session.actual_duration_seconds,
            "wrong_submission_count": session.wrong_submission_count,
            "wrong_penalty_seconds": session.wrong_penalty_seconds,
            "hint_penalty_seconds": session.hint_penalty_seconds,
            "effective_time_seconds": session.effective_time_seconds,
            "submission_lock_remaining_seconds": lock_remaining,
            "has_configured_case": bool(active_levels),
            "current_level": (
                {
                    "id": current_level.id,
                    "level_number": current_level.level_number,
                    "title": current_level.title,
                    "description": current_level.description,
                    "clue": current_level.clue,
                    "answer_type": current_level.answer_type,
                }
                if current_level
                else None
            ),
        }

    def visible_tables(self, session: Session) -> list[InvestigationTable]:
        return [
            table
            for table in self.tables
            if table.visible and table.unlock_level <= max(session.current_level_number, 1)
        ]

    def locked_table_count(self, session: Session) -> int:
        return len([table for table in self.tables if table.visible and table.unlock_level > max(session.current_level_number, 1)])

    def validate_query(self, query: str, session: Session) -> str:
        if not query or not query.strip():
            raise GameError("Write a SELECT query before running it.", 422, "query_required")
        if len(query) > 12_000:
            raise GameError("Query is too long. Keep it under 12,000 characters.", 422, "query_too_long")
        normalized = re.sub(r"/\*.*?\*/|--[^\n]*", " ", query, flags=re.S).strip()
        statements = [part.strip() for part in normalized.split(";") if part.strip()]
        if len(statements) != 1:
            raise GameError("Only one read-only statement can be run at a time.", 400, "single_statement_only")
        statement = statements[0]
        if not re.match(r"^(select|with)\b", statement, flags=re.I):
            raise GameError("Only read-only SELECT queries are allowed.", 403, "read_only_only")
        forbidden = r"\b(drop|delete|update|insert|alter|truncate|create|grant|revoke|copy|execute|call|do|merge|comment|vacuum|set|reset)\b"
        if re.search(forbidden, statement, flags=re.I):
            raise GameError("That operation is not available in the investigation terminal.", 403, "operation_blocked")
        protected = r"\b(pg_catalog|information_schema|auth|storage|game_sessions|answer_submissions|event_config|query_logs|stories|characters|red_herrings)\b"
        if re.search(protected, statement, flags=re.I):
            raise GameError("That table is not available to participant sessions.", 403, "table_protected")

        allowed = {table.name.lower() for table in self.visible_tables(session)}
        referenced = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w$]*(?:\.[a-zA-Z_][\w$]*)?)", statement, flags=re.I)
        for reference in referenced:
            table_name = reference.split(".")[-1].lower()
            if table_name not in allowed:
                raise GameError("That table is not available at the current level.", 403, "table_locked")
        return statement

    async def execute_query(self, query: str, session: Session, max_rows: int) -> QueryResult:
        safe_query = self.validate_query(query, session)
        started = perf_counter()
        await asyncio.sleep(0)
        # Empty, story-independent installs can still exercise the terminal with scalar SELECTs.
        scalar = re.fullmatch(
            r"select\s+([0-9]+|true|false|current_date)(?:\s+as\s+([a-zA-Z_][\w]*))?\s*",
            safe_query,
            flags=re.I,
        )
        if scalar:
            value = scalar.group(1)
            if value.lower() == "true":
                parsed: Any = True
            elif value.lower() == "false":
                parsed = False
            elif value.lower() == "current_date":
                parsed = now_utc().date().isoformat()
            else:
                parsed = int(value)
            columns = [scalar.group(2) or "?column?"]
            rows = [[parsed]]
        else:
            # The production adapter executes against the dedicated read-only schema.
            # Local empty mode returns a clear empty result without fabricating records.
            columns, rows = ["result"], []
        duration_ms = max(1, int((perf_counter() - started) * 1000))
        rows = rows[:max_rows]
        self.query_logs.append(QueryLog(str(uuid4()), session.id, query, True, len(rows), duration_ms))
        return QueryResult(columns, rows, len(rows), duration_ms)

    async def submit_answer(self, session: Session, answer: str) -> dict[str, Any]:
        if session.status != "IN_PROGRESS":
            raise GameError("This investigation is already finished.", 409, "session_finished")
        if not self.levels:
            raise GameError("No investigation levels have been configured yet.", 409, "case_not_configured")
        if session.last_submission_at:
            elapsed = (now_utc() - session.last_submission_at).total_seconds()
            remaining = self.event.config.wrong_answer_lock_seconds - int(elapsed)
            if remaining > 0:
                raise GameError(f"Try again in {remaining} seconds.", 429, "submission_locked")
        level = self.get_level_for_session(session)
        if not level:
            raise GameError("There is no active level for this session.", 409, "level_unavailable")
        submitted = answer.strip()
        if not submitted:
            raise GameError("Enter an answer before submitting.", 422, "answer_required")
        correct = self._compare_answer(level, submitted)
        penalty_seconds = 0
        lock_seconds = 0
        if correct:
            session.completed_level_numbers.add(level.level_number)
            next_level = next((item for item in self.levels if item.active and item.level_number > level.level_number), None)
            if next_level:
                session.current_level_number = next_level.level_number
            else:
                session.status = "COMPLETED"
                session.finish_at = now_utc()
        else:
            session.wrong_submission_count += 1
            penalty_seconds = self.event.config.wrong_answer_penalty_minutes * 60
            lock_seconds = self.event.config.wrong_answer_lock_seconds
            session.wrong_penalty_seconds += penalty_seconds
            session.last_submission_at = now_utc()
        self.answer_submissions.append(
            AnswerSubmission(str(uuid4()), session.id, level.id, submitted, correct, penalty_seconds, lock_seconds)
        )
        return {
            "correct": correct,
            "level_completed": correct,
            "next_level_unlocked": correct and session.status != "COMPLETED",
            "lock_seconds": lock_seconds,
            "penalty_seconds": penalty_seconds,
            "state": self.public_state(session),
        }

    def _compare_answer(self, level: Level, submitted: str) -> bool:
        if level.answer_type == "number":
            try:
                return any(float(submitted) == float(expected) for expected in level.answer_values)
            except ValueError:
                return False
        if level.answer_type == "exact":
            return submitted in level.answer_values
        return submitted.casefold() in {expected.casefold() for expected in level.answer_values}

    async def use_hint(self, session: Session, hint_id: str) -> dict[str, Any]:
        hint = next((item for item in self.hints if item.id == hint_id), None)
        if not hint:
            raise GameError("That hint is not available.", 404, "hint_not_found")
        if hint.level_id != (self.get_level_for_session(session).id if self.get_level_for_session(session) else None):
            raise GameError("That hint is not available at the current level.", 403, "hint_locked")
        if hint.id in session.used_hint_ids and not hint.repeatable:
            raise GameError("That hint has already been used.", 409, "hint_already_used")
        session.used_hint_ids.add(hint.id)
        session.hint_penalty_seconds += hint.penalty_minutes * 60
        return {
            "hint_id": hint.id,
            "title": hint.title,
            "body": hint.body,
            "penalty_seconds": hint.penalty_minutes * 60,
            "state": self.public_state(session),
        }

    def leaderboard(self) -> list[dict[str, Any]]:
        ranked = sorted(self.sessions.values(), key=lambda item: item.effective_time_seconds)
        return [
            {
                "rank": index + 1,
                "team_name": session.team_name,
                "current_level": session.current_level_number,
                "total_levels": len(self.levels),
                "progress_percent": round((len(session.completed_level_numbers) / len(self.levels)) * 100) if self.levels else 0,
                "effective_time_seconds": session.effective_time_seconds,
                "status": session.status,
            }
            for index, session in enumerate(ranked)
        ]