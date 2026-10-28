-- TradingQuant phase 1: OPTIONAL PostgreSQL / Supabase foundation.
-- This file is a reviewed initial schema, not an applied migration.
-- Apply only to a dedicated TradingQuant project after configuring Supabase Auth.
create extension if not exists pgcrypto;

create table if not exists public.tq_datasets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  filename text not null,
  storage_key text not null,
  symbol text,
  timeframe text,
  bar_count bigint not null check (bar_count >= 0),
  first_bar timestamptz,
  last_bar timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists tq_datasets_user_idx on public.tq_datasets(user_id, created_at desc);
alter table public.tq_datasets enable row level security;
create policy "datasets owner read" on public.tq_datasets for select to authenticated using ((select auth.uid()) = user_id);
create policy "datasets owner insert" on public.tq_datasets for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "datasets owner update" on public.tq_datasets for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "datasets owner delete" on public.tq_datasets for delete to authenticated using ((select auth.uid()) = user_id);

create table if not exists public.tq_explorations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  dataset_id uuid not null references public.tq_datasets(id) on delete restrict,
  name text not null,
  configuration jsonb not null,
  status text not null default 'queued' check (status in ('queued','running','completed','failed')),
  tested integer not null default 0 check (tested >= 0),
  accepted integer not null default 0 check (accepted >= 0),
  warning text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists tq_explorations_user_idx on public.tq_explorations(user_id, created_at desc);
alter table public.tq_explorations enable row level security;
create policy "explorations owner read" on public.tq_explorations for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "explorations owner insert" on public.tq_explorations for insert to authenticated
  with check ((select auth.uid()) = user_id and exists (
    select 1 from public.tq_datasets d where d.id = dataset_id and d.user_id = (select auth.uid())
  ));
create policy "explorations owner update" on public.tq_explorations for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id and exists (
    select 1 from public.tq_datasets d where d.id = dataset_id and d.user_id = (select auth.uid())
  ));
create policy "explorations owner delete" on public.tq_explorations for delete to authenticated
  using ((select auth.uid()) = user_id);

create table if not exists public.tq_candidates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  exploration_id uuid not null references public.tq_explorations(id) on delete cascade,
  family text not null,
  parameters jsonb not null,
  metrics_is jsonb not null,
  metrics_oos jsonb not null,
  monte_carlo jsonb not null,
  passed_preliminary boolean not null default false,
  rejection_reasons text[] not null default array[]::text[],
  created_at timestamptz not null default now()
);
create index if not exists tq_candidates_user_idx on public.tq_candidates(user_id, exploration_id);
alter table public.tq_candidates enable row level security;
create policy "candidates owner read" on public.tq_candidates for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "candidates owner insert" on public.tq_candidates for insert to authenticated
  with check ((select auth.uid()) = user_id and exists (
    select 1 from public.tq_explorations e where e.id = exploration_id and e.user_id = (select auth.uid())
  ));
create policy "candidates owner update" on public.tq_candidates for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id and exists (
    select 1 from public.tq_explorations e where e.id = exploration_id and e.user_id = (select auth.uid())
  ));
create policy "candidates owner delete" on public.tq_candidates for delete to authenticated
  using ((select auth.uid()) = user_id);

-- RLS is intentionally restrictive; this file does not enable public ANON access.
-- Restrict UPDATE/INSERT to the server in production if results must be tamper-resistant.
