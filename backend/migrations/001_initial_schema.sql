-- ============================================================
-- Stocker — Initial Schema
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Analysis Jobs
--    Stores every sentiment analysis run, keyed by task_id.
create table if not exists public.analysis_jobs (
    id          text primary key,                -- TaskIQ task_id
    ticker      text not null,
    status      text not null default 'pending', -- pending | running | completed | failed
    result      jsonb,                           -- full SentimentResult blob
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Index for the cache-first lookup: recent completed jobs for a ticker
create index if not exists idx_analysis_jobs_ticker_status
    on public.analysis_jobs (ticker, status, created_at desc);

-- 2. Watchlist Items
--    Per-user saved tickers, referencing Supabase Auth's auth.users.
create table if not exists public.watchlist_items (
    id        uuid primary key default gen_random_uuid(),
    user_id   uuid not null references auth.users(id) on delete cascade,
    ticker    text not null,
    added_at  timestamptz not null default now(),
    unique(user_id, ticker)   -- prevent duplicate saves
);

create index if not exists idx_watchlist_user
    on public.watchlist_items (user_id);

-- 3. Row Level Security
--    Watchlist: users can only read/write their own rows.
alter table public.watchlist_items enable row level security;

create policy "Users can view own watchlist"
    on public.watchlist_items for select
    using (auth.uid() = user_id);

create policy "Users can insert own watchlist"
    on public.watchlist_items for insert
    with check (auth.uid() = user_id);

create policy "Users can delete own watchlist"
    on public.watchlist_items for delete
    using (auth.uid() = user_id);

-- Analysis jobs: readable by all, writable only by service role (no RLS needed
-- since the backend uses the service-role key for writes).
alter table public.analysis_jobs enable row level security;

create policy "Anyone can read analysis jobs"
    on public.analysis_jobs for select
    using (true);

-- 4. Updated-at trigger for analysis_jobs
create or replace function public.update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_analysis_jobs_updated_at
    before update on public.analysis_jobs
    for each row
    execute function public.update_updated_at();
