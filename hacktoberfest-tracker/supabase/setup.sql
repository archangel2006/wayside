-- Hacktoberfest 2026 tracker: Supabase setup.
-- Run once in: Supabase dashboard > SQL Editor > New query > Run.
-- Safe to re-run.

-- 1) One row per user per event
create table if not exists public.event_progress (
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  event_id   text not null,
  status     text not null default '' check (status in ('', 'attended', 'missed')),
  updated_at timestamptz not null default now(),
  primary key (user_id, event_id)
);

-- Columns kept from earlier versions (check-in code, screenshot path). The app no longer
-- uses them, they are harmless, and this keeps older databases compatible.
alter table public.event_progress add column if not exists code      text not null default '';
alter table public.event_progress add column if not exists shot_path text;

-- 2) Let signed-in users reach the table through the Data API
--    (needed when "Automatically expose new tables" is turned off)
grant select, insert, update, delete on public.event_progress to authenticated;

-- 3) Row Level Security: every user can only read and write their own rows
alter table public.event_progress enable row level security;

drop policy if exists "own rows" on public.event_progress;
create policy "own rows" on public.event_progress
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
