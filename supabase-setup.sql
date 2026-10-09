-- Hacktoberfest 2026 tracker: run this once in Supabase > SQL Editor > New query.

-- 1) Table: one row per user per event
create table if not exists public.event_progress (
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  event_id   text not null,
  status     text not null default '' check (status in ('', 'attended', 'missed')),
  code       text not null default '',
  shot_path  text,
  updated_at timestamptz not null default now(),
  primary key (user_id, event_id)
);

-- 1b) Let signed-in users reach the table through the Data API (needed if "Automatically expose new tables" was off)
grant select, insert, update, delete on public.event_progress to authenticated;

-- 2) Row Level Security: each user can only touch their own rows
alter table public.event_progress enable row level security;

drop policy if exists "own rows" on public.event_progress;
create policy "own rows" on public.event_progress
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- 3) Private storage bucket for screenshots
insert into storage.buckets (id, name, public)
values ('checkins', 'checkins', false)
on conflict (id) do nothing;

-- 4) Storage policies: users can only access files under their own <user_id>/ folder
drop policy if exists "checkins select own" on storage.objects;
drop policy if exists "checkins insert own" on storage.objects;
drop policy if exists "checkins update own" on storage.objects;
drop policy if exists "checkins delete own" on storage.objects;

create policy "checkins select own" on storage.objects for select to authenticated
  using (bucket_id = 'checkins' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "checkins insert own" on storage.objects for insert to authenticated
  with check (bucket_id = 'checkins' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "checkins update own" on storage.objects for update to authenticated
  using (bucket_id = 'checkins' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "checkins delete own" on storage.objects for delete to authenticated
  using (bucket_id = 'checkins' and (storage.foldername(name))[1] = (select auth.uid())::text);
