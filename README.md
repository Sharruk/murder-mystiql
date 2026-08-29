# MURDER MYSTIQL

MURDER MYSTIQL is a story-independent investigation engine for live events. It provides the participant experience and game rules now, while keeping story content intentionally empty until an organizer configures a case.

This repository does **not** contain a murder story, fictional characters, suspects, a victim, clues, evidence, answers, red herrings, or demo case data.

## What is implemented

- Anonymous team sessions with an opaque session id
- Server-authoritative elapsed time and effective-time calculation
- Dynamic level, clue, hint, answer, and table contracts
- Separate read-only SQL query flow and answer submission flow
- Server-side SQL validation with table-access enforcement
- Configurable wrong-answer and hint penalties in the database schema
- Participant-safe leaderboard response shape
- Responsive participant investigation workspace
- Schema explorer, empty states, SQL cheatsheet, and query results table
- Separate organizer console foundation for future event management
- Separate quiz module schema for future qualification flows
- Supabase/PostgreSQL migration schema with future story entities
- Vercel configuration for a Vite static client and FastAPI function

The local API uses an in-memory repository when no database is configured. This lets the empty engine run in a fresh checkout without inventing seed data. The repository boundary in `backend/app/store.py` is where a persistent Supabase repository can be connected as event content is authored.

## Architecture

```text
React + Vite + TypeScript
          |
          | same-origin /api requests
          v
FastAPI REST API
          |
          v
Supabase PostgreSQL
  public management schema
  investigation read-only schema
```

The client never connects to PostgreSQL and never receives a service-role key. The backend owns session state, level progression, answer comparison, penalties, timer calculations, and query policy.

## Project structure

```text
.
├── api/index.py                  # Vercel FastAPI function entry point
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI application and routes
│   │   ├── models.py             # Internal domain models
│   │   ├── schemas.py            # Validated request models
│   │   ├── store.py              # Game rules and local adapter
│   │   └── config.py             # Backend-only settings
│   └── requirements.txt
├── database/schema.sql           # Supabase PostgreSQL schema
├── frontend/src/
│   ├── App.tsx                   # Landing, workspace, leaderboard, organizer views
│   ├── api.ts                    # Same-origin REST client
│   ├── types.ts                  # Client-safe response types
│   └── styles.css                # Dark investigative UI
├── index.html
├── package.json
├── vercel.json
└── .env.example
```

## Local development

Requirements: Node.js 20+ and Python 3.11+.

1. Install frontend packages:

   ```bash
   npm install
   ```

2. Install backend packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment placeholders:

   ```bash
   cp .env.example .env
   ```

4. Start both servers:

   ```bash
   npm run dev
   ```

The Vite client is available on port 5000 and proxies `/api` to FastAPI on port 8000.

Useful checks:

```bash
curl http://localhost:8000/api/health
npm run build
npm run typecheck
```

## Environment variables

Backend-only variables belong in Replit Secrets, Vercel Environment Variables, or another server-side secret store. Never prefix these with `VITE_`.

| Variable | Required for | Description |
| --- | --- | --- |
| `SESSION_SECRET` | production | Long random value reserved for future signed session cookies/tokens |
| `SUPABASE_URL` | Supabase API adapter | Project URL; never exposed to the client |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase API adapter | Backend-only service key; never commit or send to React |
| `SUPABASE_DATABASE_URL` | persistent PostgreSQL adapter | Pooler connection string for the backend |
| `ALLOWED_ORIGINS` | production | Comma-separated allowed browser origins |
| `MAX_QUERY_ROWS` | optional | Maximum participant query rows, default 200 |
| `QUERY_TIMEOUT_MS` | optional | Participant query timeout, default 3000ms |

The current local adapter reports `local-empty` from `/api/health` when `SUPABASE_DATABASE_URL` is absent. It does not create fake investigation content.

## Supabase setup

1. Create a Supabase project.
2. Open the SQL editor and run `database/schema.sql`.
3. Create an event record and matching `event_config` record when the case is ready.
4. Add story content to `stories` and its related tables.
5. Add active `game_levels` with server-only `answer_values`.
6. Add investigation tables in a dedicated `investigation` schema and map them through `investigation_tables` and `level_tables`.
7. Create a read-only investigation database role as described at the bottom of the schema file.
8. Configure backend environment variables without adding them to frontend build variables.

The schema deliberately contains no inserts. The first content migration should come from the finalized event configuration, not this engine repository.

## API structure

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API and database mode check |
| POST | `/api/game/start` | Create an anonymous session from a team name |
| GET | `/api/game/state?session_id=...` | Retrieve server-authoritative participant state |
| GET | `/api/game/levels?session_id=...` | Retrieve safe level metadata |
| GET | `/api/game/level/{level_id}?session_id=...` | Retrieve a permitted level |
| GET | `/api/schema/tables?session_id=...` | Retrieve tables currently available to the session |
| GET | `/api/schema/table/{name}?session_id=...` | Retrieve safe columns for one available table |
| POST | `/api/query/execute` | Validate and execute one read-only query |
| POST | `/api/answer/submit` | Compare an answer and advance progress server-side |
| POST | `/api/hint/use` | Apply and record a configured hint penalty |
| POST | `/api/game/finish` | Finish the current session |
| GET | `/api/leaderboard` | Retrieve participant-safe ranking aggregates |

All request bodies use Pydantic validation. The API returns safe error messages rather than stack traces.

## SQL execution and security

Participant query requests are intentionally constrained:

- only one `SELECT` or `WITH` statement is accepted
- destructive and procedural keywords are blocked server-side
- PostgreSQL/system/Supabase management tables are blocked
- table references must be in the current session's visible table allowlist
- query length, result rows, and timeout are bounded
- answer values and administrative fields are never present in client response models
- query and answer actions are separate, so running a query never adds a penalty
- future production deployment should execute using a separate read-only `investigation` role/schema

The local adapter accepts scalar queries such as `SELECT 1 AS ready` so the terminal can be exercised while the case is empty. It returns no fabricated rows for unconfigured tables.

## Future story content

When the finalized case is available, organizers add records for:

1. one `stories` record
2. story entities such as characters, locations, timeline, evidence, relationships, and red herrings
3. `investigation` schema tables and their metadata
4. `game_levels`, `level_tables`, and `level_hints`
5. server-only answer values
6. event configuration and lifecycle status

The React client already renders dynamic level and table contracts. The game rules do not depend on a particular story.

## Authentication boundary

This version deliberately has no authentication. Anonymous session ids are enough for the current participant flow. Later, Firebase or another identity provider can be introduced at the organizer/session boundary:

- keep the current game rules and progression services
- associate an authenticated identity with `game_sessions`
- add organizer authorization middleware to admin routes
- leave answer values and database credentials server-only

Do not add participant login or student verification unless that is explicitly part of a future phase.

## Vercel deployment

`vercel.json` configures Vite's `dist` output and routes `/api/*` to `api/index.py`.

1. Import the repository into Vercel.
2. Add the backend variables in the Vercel project settings.
3. Use the default build command from `vercel.json` (`npm run build`).
4. Run `database/schema.sql` in Supabase before switching an event live.
5. Set `ALLOWED_ORIGINS` to the deployed origin.

For a larger event, use Supabase's pooler connection string and the dedicated read-only investigation role. Do not use a privileged database connection for participant SQL.