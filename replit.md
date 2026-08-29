# Replit run guide

## Start the app

The `Start application` workflow runs both services:

```bash
npm run dev
```

- Vite/React preview: port 5000
- FastAPI API: port 8000
- Vite proxies `/api` requests to FastAPI during local development

## Checks

```bash
npm run typecheck
npm run build
python3 -m compileall -q backend api
```

## Environment

Copy `.env.example` to `.env` for local development. Supabase credentials are backend-only. The app intentionally runs in an empty local mode when `SUPABASE_DATABASE_URL` is not configured; no story or demo records are created.