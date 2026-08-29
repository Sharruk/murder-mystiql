from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth import create_session_jwt, decode_session_jwt, verify_firebase_id_token
from .config import get_settings
from .models import Participant, public_level
from .schemas import (
    AnswerRequest,
    AuthResponse,
    AuthVerifyRequest,
    FinishRequest,
    HintRequest,
    ParticipantOut,
    QueryRequest,
    QuizSubmitRequest,
    StartGameRequest,
)
from .store import GameError, GameStore

logger = logging.getLogger("murder_mystiql")
settings = get_settings()
store = GameStore()

app = FastAPI(
    title="MURDER MYSTIQL: LCU ECLIPSE API",
    version="1.0.0",
    description="Invente 2026 SQL Investigation Case Engine with SSN Firebase Authentication.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(GameError)
async def game_error_handler(_: Request, exc: GameError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"message": exc.message, "code": exc.code}},
    )


async def get_current_participant(request: Request) -> Participant:
    """Extract and cryptographically verify authentication token."""
    auth_header = request.headers.get("Authorization") or request.headers.get("x-session-token")
    token: str | None = None

    if auth_header:
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        else:
            token = auth_header.strip()

    if not token:
        # Fallback to query parameter if provided
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Authentication required. Please sign in with your SSN Google account."},
        )

    # 1. Try decoding application JWT session token
    try:
        payload = decode_session_jwt(token)
        uid = payload.get("sub")
        participant = store.get_participant_by_firebase_uid(uid)
        if participant:
            return participant

        # If participant was in JWT but not yet in memory store, rebuild
        email = payload.get("email", "")
        name = payload.get("name")
        is_qual = payload.get("is_qualified", False)
        return await store.get_or_create_participant(uid, email, name, email_verified=True)
    except HTTPException:
        # 2. Try direct Firebase ID token verification
        try:
            fb_decoded = verify_firebase_id_token(token)
            uid = fb_decoded.get("uid")
            email = fb_decoded.get("email")
            name = fb_decoded.get("name")
            pic = fb_decoded.get("picture")
            return await store.get_or_create_participant(uid, email, name, pic, email_verified=True)
        except Exception as ex:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_token", "message": f"Authentication failed: {ex}"},
            )


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    db_status = "configured" if settings.supabase_database_url else "local-seeded"
    return {
        "status": "ok",
        "service": "murder-mystiql-invente-2026",
        "database": db_status,
        "story": store.event.story.title,
    }


# =========================================================
# Authentication Endpoints
# =========================================================

@app.post("/api/auth/verify", response_model=AuthResponse)
async def auth_verify(payload: AuthVerifyRequest) -> AuthResponse:
    """Verify Firebase ID token, enforce @ssn.edu.in, and issue application session."""
    decoded = verify_firebase_id_token(payload.id_token)
    uid = decoded["uid"]
    email = decoded["email"]
    name = decoded.get("name")
    picture = decoded.get("picture")

    participant = await store.get_or_create_participant(
        firebase_uid=uid,
        email=email,
        display_name=name,
        photo_url=picture,
        email_verified=True,
    )

    token = create_session_jwt(participant)

    # Get or restore active game session for this participant
    team_name = participant.display_name or participant.email.split("@")[0]
    session = await store.start_session(team_name=team_name, participant=participant)

    return AuthResponse(
        token=token,
        participant=ParticipantOut(
            id=participant.id,
            firebase_uid=participant.firebase_uid,
            email=participant.email,
            display_name=participant.display_name,
            photo_url=participant.photo_url,
            is_qualified=participant.is_qualified or session.quiz_passed,
        ),
        session=store.public_state(session),
    )


@app.get("/api/auth/me")
async def auth_me(current_user: Participant = Depends(get_current_participant)) -> dict[str, Any]:
    """Retrieve profile and session for current authenticated SSN participant."""
    session = store.get_participant_session(current_user)
    return {
        "participant": {
            "id": current_user.id,
            "firebase_uid": current_user.firebase_uid,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "photo_url": current_user.photo_url,
            "is_qualified": current_user.is_qualified or (session.quiz_passed if session else False),
        },
        "session": store.public_state(session) if session else None,
    }


@app.post("/api/auth/logout")
async def auth_logout() -> dict[str, str]:
    return {"status": "ok", "message": "Signed out successfully."}


# =========================================================
# Game & Investigation Endpoints (Protected)
# =========================================================

@app.post("/api/game/start")
async def start_game(
    payload: StartGameRequest,
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    team_name = payload.team_name or current_user.display_name or current_user.email.split("@")[0]
    session = await store.start_session(team_name=team_name, participant=current_user)
    return {"session": store.public_state(session)}


@app.get("/api/game/state")
async def game_state(
    session_id: str = Query(min_length=1, max_length=100),
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(session_id)
    return {"session": store.public_state(session)}


@app.get("/api/game/levels")
async def game_levels(
    session_id: str = Query(min_length=1, max_length=100),
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(session_id)
    return {"levels": [public_level(level, session) for level in store.levels]}


@app.get("/api/game/level/{level_id}")
async def game_level(
    level_id: str,
    session_id: str = Query(min_length=1, max_length=100),
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(session_id)
    level = store.get_level_for_session(session, level_id)
    if not level:
        raise GameError("Level not found.", 404, "level_not_found")
    return {"level": public_level(level, session)}


@app.get("/api/schema/tables")
async def schema_tables(
    session_id: str = Query(min_length=1, max_length=100),
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(session_id)
    available = [
        {
            "name": table.name,
            "label": table.label,
            "unlock_level": table.unlock_level,
            "description": table.description,
            "columns": [
                {
                    "name": column.name,
                    "data_type": column.data_type,
                    "nullable": column.nullable,
                    "is_primary_key": column.is_primary_key,
                }
                for column in table.columns
            ],
        }
        for table in store.visible_tables(session)
    ]
    return {
        "available_tables": available,
        "locked_table_count": store.locked_table_count(session),
        "total_tables": len(store.tables),
    }


@app.get("/api/schema/table/{table_name}")
async def schema_table(
    table_name: str,
    session_id: str = Query(min_length=1, max_length=100),
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(session_id)
    table = next((item for item in store.visible_tables(session) if item.name == table_name), None)
    if not table:
        raise GameError("That table is not available at your current level.", 403, "table_locked")
    return {
        "table": {
            "name": table.name,
            "label": table.label,
            "description": table.description,
            "columns": [column.__dict__ for column in table.columns],
        }
    }


@app.post("/api/query/execute")
async def execute_query(
    payload: QueryRequest,
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(payload.session_id)
    result = await store.execute_query(payload.query, session, settings.max_query_rows)
    return {
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "duration_ms": result.duration_ms,
        "max_rows": settings.max_query_rows,
    }


@app.post("/api/answer/submit")
async def submit_answer(
    payload: AnswerRequest,
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(payload.session_id)
    return await store.submit_answer(session, payload.answer)


@app.post("/api/hint/use")
async def use_hint(
    payload: HintRequest,
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(payload.session_id)
    return await store.use_hint(session, payload.hint_id)


@app.post("/api/game/finish")
async def finish_game(
    payload: FinishRequest,
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    session = store.get_session(payload.session_id)
    if session.status == "IN_PROGRESS":
        session.status = "FINISHED"
        session.finish_at = session.finish_at or __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    return {"session": store.public_state(session)}


@app.get("/api/quiz/questions")
async def quiz_questions() -> dict:
    return {"questions": store.get_quiz_questions()}


@app.post("/api/quiz/submit")
async def quiz_submit(
    payload: QuizSubmitRequest,
    current_user: Participant = Depends(get_current_participant),
) -> dict:
    return store.evaluate_quiz(payload.session_id, payload.answers)


# =========================================================
# Public & Organizer Telemetry
# =========================================================

@app.get("/api/leaderboard")
async def leaderboard() -> dict:
    """Public leaderboard view (team name, rank, progress, and effective time only)."""
    return {
        "event": {
            "name": store.event.name,
            "slug": store.event.slug,
            "disclaimer": store.event.story.disclaimer,
        },
        "entries": store.leaderboard(),
    }


@app.get("/api/organizer/stats")
async def organizer_stats() -> dict:
    """Aggregated event metrics without leaking private keys or participant passwords."""
    sessions = list(store.sessions.values())
    active_count = sum(1 for s in sessions if s.status == "IN_PROGRESS")
    completed_count = sum(1 for s in sessions if s.status == "COMPLETED")
    return {
        "event_name": store.event.name,
        "total_sessions": len(sessions),
        "active_sessions": active_count,
        "completed_sessions": completed_count,
        "total_levels": len(store.levels),
        "total_tables": len(store.tables),
        "wrong_penalty_minutes": store.event.config.wrong_answer_penalty_minutes,
        "hint_penalty_minutes": store.event.config.hint_penalty_default_minutes,
        "leaderboard": store.leaderboard(),
    }