-- MURDER MYSTIQL: LCU ECLIPSE
-- Migration: Firebase Authentication & SSN Institutional Accounts
-- Idempotent migration to add participants table and associate game sessions.

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

-- Associate game sessions with authenticated participants
do $$
begin
  if not exists (
    select 1 from information_schema.columns 
    where table_schema = 'public' 
    and table_name = 'game_sessions' 
    and column_name = 'participant_id'
  ) then
    alter table public.game_sessions 
      add column participant_id uuid references public.participants(id) on delete set null;
  end if;
end $$;

-- Enforce one active/completed participation per participant per event
create unique index if not exists game_sessions_event_participant 
  on public.game_sessions(event_id, participant_id) 
  where participant_id is not null;

create index if not exists participants_firebase_uid 
  on public.participants(firebase_uid);

create index if not exists participants_email 
  on public.participants(email);
