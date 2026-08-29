-- MURDER MYSTIQL
-- Story-independent event engine schema for Supabase PostgreSQL.
-- No story, levels, investigation tables, answers, or demo records are seeded.

create extension if not exists pgcrypto;

create type public.event_status as enum ('draft', 'live', 'paused', 'archived');
create type public.session_status as enum ('IN_PROGRESS', 'COMPLETED', 'FINISHED');
create type public.answer_type as enum ('text', 'number', 'exact', 'case_insensitive');

create table public.events (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9-]+$'),
  name text not null,
  tagline text,
  description text,
  status public.event_status not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.event_config (
  event_id uuid primary key references public.events(id) on delete cascade,
  wrong_answer_penalty_minutes integer not null default 5 check (wrong_answer_penalty_minutes >= 0),
  wrong_answer_lock_seconds integer not null default 60 check (wrong_answer_lock_seconds >= 0),
  hint_penalty_default_minutes integer not null default 2 check (hint_penalty_default_minutes >= 0),
  allow_pause boolean not null default false,
  max_query_rows integer not null default 200 check (max_query_rows between 1 and 1000),
  query_timeout_ms integer not null default 3000 check (query_timeout_ms between 100 and 30000),
  updated_at timestamptz not null default now()
);

create table public.stories (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null unique references public.events(id) on delete cascade,
  title text,
  prologue text,
  description text,
  status text not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.characters (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references public.stories(id) on delete cascade,
  name text not null,
  role text,
  description text,
  metadata jsonb not null default '{}'::jsonb
);

create table public.locations (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references public.stories(id) on delete cascade,
  name text not null,
  description text,
  metadata jsonb not null default '{}'::jsonb
);

create table public.timeline_entries (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references public.stories(id) on delete cascade,
  occurred_at timestamptz,
  title text not null,
  description text,
  metadata jsonb not null default '{}'::jsonb
);

create table public.evidence (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references public.stories(id) on delete cascade,
  name text not null,
  description text,
  evidence_type text,
  metadata jsonb not null default '{}'::jsonb
);

create table public.relationships (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references public.stories(id) on delete cascade,
  source_character_id uuid references public.characters(id) on delete set null,
  target_character_id uuid references public.characters(id) on delete set null,
  relationship_type text not null,
  description text
);

create table public.red_herrings (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references public.stories(id) on delete cascade,
  title text not null,
  description text,
  metadata jsonb not null default '{}'::jsonb
);

create table public.game_levels (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  level_number integer not null check (level_number > 0),
  title text not null,
  description text,
  clue text,
  answer_type public.answer_type not null default 'case_insensitive',
  -- This field is server-only. Never include it in participant response models.
  answer_values jsonb not null default '[]'::jsonb,
  active boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (event_id, level_number)
);

create table public.investigation_tables (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  table_name text not null check (table_name ~ '^[a-z_][a-z0-9_]*$'),
  display_label text not null,
  schema_name text not null default 'investigation',
  description text,
  metadata jsonb not null default '{}'::jsonb,
  unique (event_id, table_name)
);

create table public.level_tables (
  level_id uuid not null references public.game_levels(id) on delete cascade,
  table_id uuid not null references public.investigation_tables(id) on delete cascade,
  is_visible boolean not null default true,
  primary key (level_id, table_id)
);

create table public.level_hints (
  id uuid primary key default gen_random_uuid(),
  level_id uuid not null references public.game_levels(id) on delete cascade,
  title text not null,
  body text not null,
  penalty_minutes integer not null default 2 check (penalty_minutes >= 0),
  repeatable boolean not null default false,
  sort_order integer not null default 0
);

create table public.game_sessions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete restrict,
  -- Anonymous access is represented by an opaque session id for this version.
  -- Add an identity/provider reference here later without changing game rules.
  team_name text not null check (char_length(team_name) between 1 and 80),
  started_at timestamptz not null default now(),
  finish_at timestamptz,
  current_level_number integer not null default 1 check (current_level_number >= 0),
  wrong_submission_count integer not null default 0 check (wrong_submission_count >= 0),
  wrong_penalty_seconds integer not null default 0 check (wrong_penalty_seconds >= 0),
  hint_penalty_seconds integer not null default 0 check (hint_penalty_seconds >= 0),
  status public.session_status not null default 'IN_PROGRESS',
  created_at timestamptz not null default now()
);

create table public.game_progress (
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  level_id uuid not null references public.game_levels(id) on delete cascade,
  completed_at timestamptz,
  primary key (session_id, level_id)
);

create table public.answer_submissions (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  level_id uuid not null references public.game_levels(id) on delete restrict,
  submitted_answer text not null,
  correct boolean not null,
  penalty_seconds integer not null default 0 check (penalty_seconds >= 0),
  lock_seconds integer not null default 0 check (lock_seconds >= 0),
  created_at timestamptz not null default now()
);

create table public.hint_usage (
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  hint_id uuid not null references public.level_hints(id) on delete restrict,
  used_at timestamptz not null default now(),
  penalty_seconds integer not null default 0 check (penalty_seconds >= 0),
  primary key (session_id, hint_id)
);

create table public.query_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  query_hash text not null,
  query_length integer not null check (query_length > 0),
  success boolean not null,
  row_count integer not null default 0 check (row_count >= 0),
  duration_ms integer not null default 0 check (duration_ms >= 0),
  error_code text,
  created_at timestamptz not null default now()
);

create index game_levels_event_order on public.game_levels(event_id, level_number);
create index game_sessions_event_status on public.game_sessions(event_id, status);
create index answer_submissions_session_time on public.answer_submissions(session_id, created_at desc);
create index query_logs_session_time on public.query_logs(session_id, created_at desc);

-- Quiz module is intentionally separate from investigation progression.
create table public.quiz_questions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  prompt text not null,
  points integer not null default 1 check (points >= 0),
  time_limit_seconds integer check (time_limit_seconds is null or time_limit_seconds > 0),
  active boolean not null default false,
  sort_order integer not null default 0
);

create table public.quiz_options (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.quiz_questions(id) on delete cascade,
  option_text text not null,
  is_correct boolean not null default false
);

create table public.quiz_attempts (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  team_name text not null,
  score integer not null default 0 check (score >= 0),
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

-- Leaderboard view intentionally exposes only participant-safe aggregate fields.
create or replace view public.leaderboard as
select
  dense_rank() over (partition by event_id order by
    (extract(epoch from (coalesce(finish_at, now()) - started_at))::bigint
      + wrong_penalty_seconds + hint_penalty_seconds)
  )::integer as rank,
  event_id,
  team_name,
  current_level_number,
  wrong_submission_count,
  wrong_penalty_seconds,
  hint_penalty_seconds,
  extract(epoch from (coalesce(finish_at, now()) - started_at))::bigint as actual_duration_seconds,
  (
    extract(epoch from (coalesce(finish_at, now()) - started_at))::bigint
    + wrong_penalty_seconds + hint_penalty_seconds
  ) as effective_time_seconds,
  status
from public.game_sessions;

-- In production, participant SQL should use a separate read-only database role
-- with a dedicated investigation schema. Keep management tables out of its search path.
-- Apply the following after creating and populating investigation tables:
--
-- create schema if not exists investigation;
-- create role murder_mystiql_reader nologin;
-- revoke all on schema public from murder_mystiql_reader;
-- grant usage on schema investigation to murder_mystiql_reader;
-- grant select on all tables in schema investigation to murder_mystiql_reader;
-- alter default privileges in schema investigation grant select on tables to murder_mystiql_reader;