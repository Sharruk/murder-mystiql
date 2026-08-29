-- MURDER MYSTIQL: LCU ECLIPSE
-- Complete production schema for Supabase PostgreSQL (Session Pooler & Direct).

create extension if not exists pgcrypto;

-- Enums (Idempotent creation)
do $$
begin
  if not exists (select 1 from pg_type where typname = 'event_status') then
    create type public.event_status as enum ('draft', 'live', 'paused', 'archived');
  end if;
  if not exists (select 1 from pg_type where typname = 'session_status') then
    create type public.session_status as enum ('IN_PROGRESS', 'COMPLETED', 'FINISHED');
  end if;
  if not exists (select 1 from pg_type where typname = 'answer_type') then
    create type public.answer_type as enum ('text', 'number', 'exact', 'case_insensitive');
  end if;
end $$;

-- Public Event Management Tables
create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9-]+$'),
  name text not null,
  tagline text,
  description text,
  status public.event_status not null default 'live',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.event_config (
  event_id uuid primary key references public.events(id) on delete cascade,
  wrong_answer_penalty_minutes integer not null default 5 check (wrong_answer_penalty_minutes >= 0),
  wrong_answer_lock_seconds integer not null default 60 check (wrong_answer_lock_seconds >= 0),
  hint_penalty_default_minutes integer not null default 2 check (hint_penalty_default_minutes >= 0),
  allow_pause boolean not null default false,
  max_query_rows integer not null default 200 check (max_query_rows between 1 and 1000),
  query_timeout_ms integer not null default 3000 check (query_timeout_ms between 100 and 30000),
  quiz_required boolean not null default false,
  quiz_qualify_score integer not null default 3 check (quiz_qualify_score >= 0),
  updated_at timestamptz not null default now()
);

create table if not exists public.stories (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null unique references public.events(id) on delete cascade,
  title text not null,
  prologue text,
  description text,
  disclaimer text,
  status text not null default 'live',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.game_levels (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  level_number integer not null check (level_number > 0),
  title text not null,
  narrative_context text,
  objective text not null,
  clue text,
  answer_type public.answer_type not null default 'case_insensitive',
  -- Server-only answers array. Never send to participants.
  answer_values jsonb not null default '[]'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (event_id, level_number)
);

create table if not exists public.investigation_tables (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  table_name text not null check (table_name ~ '^[a-z_][a-z0-9_]*$'),
  display_label text not null,
  schema_name text not null default 'investigation',
  unlock_level integer not null default 1 check (unlock_level > 0),
  description text,
  columns_metadata jsonb not null default '[]'::jsonb,
  unique (event_id, table_name)
);

create table if not exists public.level_tables (
  level_id uuid not null references public.game_levels(id) on delete cascade,
  table_id uuid not null references public.investigation_tables(id) on delete cascade,
  is_visible boolean not null default true,
  primary key (level_id, table_id)
);

create table if not exists public.level_hints (
  id uuid primary key default gen_random_uuid(),
  level_id uuid not null references public.game_levels(id) on delete cascade,
  title text not null,
  body text not null,
  penalty_minutes integer not null default 2 check (penalty_minutes >= 0),
  repeatable boolean not null default false,
  sort_order integer not null default 0
);

create table if not exists public.participants (
  id uuid primary key default gen_random_uuid(),
  firebase_uid text not null unique,
  email text not null unique check (email ~* '^[A-Za-z0-9._%+-]+@ssn\.edu\.in$'),
  display_name text,
  photo_url text,
  email_verified boolean not null default true,
  is_qualified boolean not null default false,
  created_at timestamptz not null default now(),
  last_login_at timestamptz not null default now()
);

create table if not exists public.game_sessions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete restrict,
  participant_id uuid references public.participants(id) on delete set null,
  team_name text not null check (char_length(team_name) between 1 and 80),
  started_at timestamptz not null default now(),
  finish_at timestamptz,
  current_level_number integer not null default 1 check (current_level_number >= 0),
  wrong_submission_count integer not null default 0 check (wrong_submission_count >= 0),
  wrong_penalty_seconds integer not null default 0 check (wrong_penalty_seconds >= 0),
  hint_penalty_seconds integer not null default 0 check (hint_penalty_seconds >= 0),
  status public.session_status not null default 'IN_PROGRESS',
  last_submission_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.game_progress (
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  level_id uuid not null references public.game_levels(id) on delete cascade,
  completed_at timestamptz not null default now(),
  primary key (session_id, level_id)
);

create table if not exists public.answer_submissions (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  level_id uuid not null references public.game_levels(id) on delete restrict,
  submitted_answer text not null,
  correct boolean not null,
  penalty_seconds integer not null default 0 check (penalty_seconds >= 0),
  lock_seconds integer not null default 0 check (lock_seconds >= 0),
  created_at timestamptz not null default now()
);

create table if not exists public.hint_usage (
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  hint_id uuid not null references public.level_hints(id) on delete restrict,
  used_at timestamptz not null default now(),
  penalty_seconds integer not null default 0 check (penalty_seconds >= 0),
  primary key (session_id, hint_id)
);

create table if not exists public.query_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.game_sessions(id) on delete cascade,
  query_hash text not null,
  query_text text,
  query_length integer not null check (query_length > 0),
  success boolean not null,
  row_count integer not null default 0 check (row_count >= 0),
  duration_ms integer not null default 0 check (duration_ms >= 0),
  error_code text,
  created_at timestamptz not null default now()
);

create table if not exists public.quiz_questions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  prompt text not null,
  points integer not null default 1 check (points >= 0),
  time_limit_seconds integer check (time_limit_seconds is null or time_limit_seconds > 0),
  active boolean not null default true,
  sort_order integer not null default 0
);

create table if not exists public.quiz_options (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.quiz_questions(id) on delete cascade,
  option_text text not null,
  is_correct boolean not null default false
);

create table if not exists public.quiz_attempts (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  session_id uuid references public.game_sessions(id) on delete set null,
  team_name text not null,
  score integer not null default 0 check (score >= 0),
  qualified boolean not null default true,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists game_levels_event_order on public.game_levels(event_id, level_number);
create index if not exists game_sessions_event_status on public.game_sessions(event_id, status);
create index if not exists answer_submissions_session_time on public.answer_submissions(session_id, created_at desc);
create index if not exists query_logs_session_time on public.query_logs(session_id, created_at desc);

-- Leaderboard View
create or replace view public.leaderboard as
select
  dense_rank() over (
    partition by event_id 
    order by 
      case when status = 'COMPLETED' then 0 else 1 end,
      current_level_number desc,
      (extract(epoch from (coalesce(finish_at, now()) - started_at))::bigint
        + wrong_penalty_seconds + hint_penalty_seconds) asc
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

-- ==========================================================
-- INVESTIGATION SCHEMA (Case Data for SQL Terminal Queries)
-- ==========================================================

create schema if not exists investigation;

create table if not exists investigation.shipments (
  shipment_id text primary key,
  container_number text not null,
  vessel_name text,
  imo_number text,
  declared_manifest text not null,
  actual_cargo text not null,
  origin text not null,
  destination text not null,
  arrival_timestamp timestamptz not null,
  clearance_status text not null
);

create table if not exists investigation.access_logs (
  log_id text primary key,
  card_or_badge_id text not null,
  user_name text not null,
  facility_location text not null,
  access_timestamp timestamptz not null,
  action_description text not null
);

create table if not exists investigation.vehicle_records (
  vehicle_id text primary key,
  registration_number text not null,
  vehicle_type text not null,
  registered_owner text not null,
  sighting_location text not null,
  sighting_timestamp timestamptz not null
);

create table if not exists investigation.phone_records (
  call_id text primary key,
  caller_imsi text not null,
  receiver_imsi text not null,
  caller_name text,
  receiver_name text,
  call_timestamp timestamptz not null,
  duration_seconds integer not null,
  cell_tower text not null,
  notes text
);

create table if not exists investigation.messages (
  message_id text primary key,
  sender text not null,
  receiver text not null,
  sent_timestamp timestamptz not null,
  message_text text not null,
  encryption_type text not null default 'Plaintext'
);

create table if not exists investigation.bank_transactions (
  transaction_id text primary key,
  sender_account text not null,
  receiver_account text not null,
  amount numeric(14, 2) not null,
  transaction_type text not null,
  reference_number text not null unique,
  transaction_timestamp timestamptz not null
);

create table if not exists investigation.evidence (
  evidence_id text primary key,
  item_name text not null,
  recovered_location text not null,
  recovery_timestamp timestamptz not null,
  forensic_summary text not null,
  matching_suspect text
);

create table if not exists investigation.characters (
  character_id text primary key,
  full_name text not null,
  alias text,
  primary_role text not null,
  location_base text not null,
  organization text not null,
  status text not null
);

create table if not exists investigation.locations (
  location_id text primary key,
  name text not null,
  state text not null,
  latitude numeric(9, 4),
  longitude numeric(9, 4),
  description text,
  significance text not null
);

create table if not exists investigation.timeline_events (
  event_code text primary key,
  occurred_at timestamptz not null,
  location_name text not null,
  title text not null,
  summary text not null,
  key_individuals text not null
);

create table if not exists investigation.relationships (
  relationship_id text primary key,
  person_a text not null,
  person_b text not null,
  relationship_type text not null,
  details text not null
);

create table if not exists investigation.red_herrings (
  record_id text primary key,
  lead_code text not null,
  apparent_theory text not null,
  forensic_truth text not null,
  debunking_evidence text not null
);

create table if not exists investigation.autopsies (
  autopsy_id text primary key,
  victim_name text not null,
  time_of_death timestamptz not null,
  location_found text not null,
  cause_of_death text not null,
  killer_name text not null,
  motive text not null
);

create table if not exists investigation.kill_records (
  record_id text primary key,
  victim text not null,
  killer text not null,
  weapon text not null,
  date_time timestamptz not null,
  location text not null,
  plot_impact text not null
);