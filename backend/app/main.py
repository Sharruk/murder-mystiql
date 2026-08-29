from __future__ import annotations

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .models import public_level
from .schemas import AnswerRequest, FinishRequest, HintRequest, QueryRequest, StartGameRequest
from .store import GameError, GameStore

settings = get_settings()
store = GameStore()

app = FastAPI(
    title="MURDER MYSTIQL API",
    version="0.1.0",
    description="Story-independent investigation game engine.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(GameError)
async def game_error_handler(_: Request, exc: GameError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": {"message": exc.message, "code": exc.code}})


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    return {"status": "ok", "service": "murder-mystiql-api", "database": "configured" if settings.supabase_database_url else "local-empty"}


@app.post("/api/game/start")
async def start_game(payload: StartGameRequest) -> dict:
    session = await store.start_session(payload.team_name)
    return {"session": store.public_state(session)}


@app.get("/api/game/state")
async def game_state(session_id: str = Query(min_length=1, max_length=100)) -> dict:
    return {"session": store.public_state(store.get_session(session_id))}


@app.get("/api/game/levels")
async def game_levels(session_id: str = Query(min_length=1, max_length=100)) -> dict:
    session = store.get_session(session_id)
    return {"levels": [public_level(level, session) for level in store.levels]}


@app.get("/api/game/level/{level_id}")
async def game_level(level_id: str, session_id: str = Query(min_length=1, max_length=100)) -> dict:
    session = store.get_session(session_id)
    level = store.get_level_for_session(session, level_id)
    if not level:
        raise GameError("Level not found.", 404, "level_not_found")
    return {"level": public_level(level, session)}


@app.get("/api/schema/tables")
async def schema_tables(session_id: str = Query(min_length=1, max_length=100)) -> dict:
    session = store.get_session(session_id)
    available = [
        {
            "name": table.name,
            "label": table.label,
            "unlock_level": table.unlock_level,
            "columns": [{"name": column.name, "data_type": column.data_type, "nullable": column.nullable, "is_primary_key": column.is_primary_key} for column in table.columns],
        }
        for table in store.visible_tables(session)
    ]
    return {"available_tables": available, "locked_table_count": store.locked_table_count(session)}


@app.get("/api/schema/table/{table_name}")
async def schema_table(table_name: str, session_id: str = Query(min_length=1, max_length=100)) -> dict:
    session = store.get_session(session_id)
    table = next((item for item in store.visible_tables(session) if item.name == table_name), None)
    if not table:
        raise GameError("That table is not available at the current level.", 403, "table_locked")
    return {"table": {"name": table.name, "label": table.label, "columns": [column.__dict__ for column in table.columns]}}


@app.post("/api/query/execute")
async def execute_query(payload: QueryRequest) -> dict:
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
async def submit_answer(payload: AnswerRequest) -> dict:
    session = store.get_session(payload.session_id)
    return await store.submit_answer(session, payload.answer)


@app.post("/api/hint/use")
async def use_hint(payload: HintRequest) -> dict:
    session = store.get_session(payload.session_id)
    return await store.use_hint(session, payload.hint_id)


@app.post("/api/game/finish")
async def finish_game(payload: FinishRequest) -> dict:
    session = store.get_session(payload.session_id)
    if session.status == "IN_PROGRESS":
        session.status = "FINISHED"
        session.finish_at = session.finish_at or __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    return {"session": store.public_state(session)}


@app.get("/api/leaderboard")
async def leaderboard() -> dict:
    return {"event": {"name": store.event.name, "slug": store.event.slug}, "entries": store.leaderboard()}