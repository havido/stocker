# Stocker — System Design & Engineering Document

> A distributed, real-time stock **sentiment analysis** application. Users search a
> ticker; the system scrapes social/news text, runs **FinBERT** NLP to grade
> sentiment (Strong Buy → Strong Sell), generates an **LLM investment summary**,
> and **streams live progress** to the browser — all while keeping the web tier
> isolated from heavy ML so it stays responsive under load.
>
> This document is written so a new engineer (or an AI) can understand the system
> as if they designed it: the requirements, the architecture, every data flow, the
> data model, the trade-offs, the war stories, and a plan to scale it to millions.

---

## 1. Problem statement & product

**Stocker correlates stock price movement with live market sentiment.** For any
ticker, it:

1. shows a **price chart** across multiple ranges,
2. scrapes recent **Reddit + Yahoo Finance** discussion/news,
3. runs **FinBERT** (a finance-tuned BERT) to classify each text as
   positive/negative/neutral and aggregates a **5-tier grade**,
4. generates a **bull/bear/bottom-line AI summary** from the evidence,
5. **streams the analysis progress live** ("Scraping Reddit…", "FinBERT batch 2/5…"),
6. lets users **save tickers to a watchlist**.

The interesting engineering is *not* the ML — it's that the architecture is
**dictated by two hostile realities**: (a) ML inference is slow and memory-hungry,
and (b) third-party data sources (Reddit, Yahoo) are unreliable and aggressively
rate-limited. Every major design decision falls out of those two facts.

---

## 2. Requirements

### Functional
- Register / log in (email + password).
- View a price chart over **1D, 1M, 6M, YTD, 1Y, 5Y, 10Y**.
- Search any stock ticker.
- See **live, streaming** progress of the analysis.
- Trigger / view a **5-tier sentiment grade** *and the sources it was graded from*.
- See an **AI summary**.
- Save tickers and view the saved list.

### Non-functional (the design drivers)
| NFR | Target | Why it shapes the design |
|---|---|---|
| **Low-latency streaming** | <500 ms per progress update; <60 s end-to-end | Forces an async job + push model (SSE), not a blocking request. |
| **High availability & fault isolation** | The web API stays responsive **even if ML workers exhaust CPU/RAM** | Forces a **physical producer/consumer split** — the API must not run ML. |
| **Fault tolerance** | Gracefully survive **aggressive throttling** from Reddit/Yahoo | Forces defensive scraping, graceful degradation, and (eventually) caching/precompute. |

---

## 3. High-level architecture

Five physically-partitioned tiers, decoupled by a Redis broker:

```
            ┌──────────────┐     HTTPS / SSE      ┌─────────────────────────┐
            │   Browser    │◄────────────────────►│   Frontend (Vercel)     │
            │  (React SPA) │                      │  React + Vite + TS      │
            └──────────────┘                      └───────────┬─────────────┘
                                                              │ REST + SSE (VITE_API_URL)
                                                              ▼
                                            ┌─────────────────────────────────┐
                                            │  API Gateway / PRODUCER (Render) │
                                            │  FastAPI (NO ML deps)            │
                                            │  • auth routing                  │
                                            │  • cache-first dispatch          │
                                            │  • enqueue jobs (AsyncKicker)    │
                                            │  • SSE: subscribe Redis pub/sub  │
                                            └───┬───────────────┬─────────────┘
                                  enqueue/cache │               │ auth + DB (REST)
                                                ▼               ▼
                       ┌────────────────────────────────┐   ┌──────────────────────────┐
                       │  Upstash Redis (rediss:// TLS)  │   │  Supabase (Postgres+Auth)│
                       │  • Task queue (ListQueueBroker) │   │  • analysis_jobs         │
                       │  • Pub/Sub backplane (SSE)      │   │  • watchlist_items (RLS) │
                       │  • LRU/TTL cache                │   │  • Auth (JWT)            │
                       └───┬─────────────────────────────┘   └──────────────────────────┘
                  pull job │  ▲ publish progress + result
                           ▼  │
            ┌─────────────────────────────────────────────┐
            │  ML Worker / CONSUMER (GCP Compute Engine)   │
            │  TaskIQ worker (heavyweight, memory-capped)  │
            │  Pipeline: scrape → FinBERT → LLM → persist  │
            │  • BeautifulSoup scrapers (Reddit/Yahoo)     │
            │  • PyTorch + transformers (FinBERT, CPU)     │
            │  • Groq (Llama 3.3) summary                  │
            └─────────────────────────────────────────────┘
```

### The single most important design decision
**The API and the ML worker are separate processes, on separate machines, that
share *only* a Redis broker.** The API server's dependency image deliberately
**excludes torch/transformers** (`requirements-api.txt` vs `requirements-worker.txt`).
It enqueues work by *task name* using TaskIQ's `AsyncKicker` and **never imports the
worker code** (`tasks.py`). Consequences:

- If FinBERT OOMs or pins CPU, the **API is unaffected** — jobs simply queue
  (satisfies the availability/fault-isolation NFR directly).
- The API image is tiny and boots fast; the worker image is huge and slow — and
  that's fine because they scale independently.
- The two tiers can be written, deployed, and scaled separately.

This is the heart of the system and the thing to lead a presentation with.

---

## 4. Tech stack

| Tier | Tech |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts, React Router, TanStack Query, `sonner` toasts |
| **API (Producer)** | FastAPI, Uvicorn, Pydantic, `supabase-py`, `redis`/`redis.asyncio`, TaskIQ + `taskiq-redis`, yfinance |
| **Worker (Consumer)** | TaskIQ, PyTorch + `transformers` (FinBERT `ProsusAI/finbert`), BeautifulSoup4, `requests`, yfinance, Groq (OpenAI-compatible) |
| **Broker / Cache** | Upstash Redis (TLS) — queue + pub/sub + cache |
| **Database / Auth** | Supabase (Postgres + PostgREST + Supabase Auth / JWT, Row-Level Security) |
| **Hosting** | Vercel (frontend), Render (API), GCP Compute Engine (worker) |

---

## 5. Component deep-dives

### 5.1 Frontend (Vercel)
- **SPA** (React + Vite). `VITE_API_URL` is inlined at **build time** → must redeploy
  to change the API target. `vercel.json` rewrites all routes to `/index.html` for
  client-side routing.
- **Auth:** a JWT (Supabase access token) is stored in `localStorage`; `AuthContext`
  restores it on load. A **centralized API client** (`lib/api.ts`) injects
  `Authorization: Bearer` and handles `401` globally — *except* on `/v1/auth/*`, so a
  bad-login `401` surfaces its message instead of triggering a redirect loop.
- **Email-confirmation callback:** Supabase implicit-flow returns the session in the
  URL hash (`/#access_token=…`); `AuthProvider` parses it on load, establishes the
  session, and cleans the URL.
- **Analysis UX state machine:** `idle → loading → completed | error`. On "loading"
  it opens an `EventSource` (SSE) and renders streamed step messages; on the terminal
  sentinel it fetches the final result.
- **Chart:** Recharts line chart with 7 period buttons; gain/loss is **period-aware**
  (see §10.3).

### 5.2 API Gateway / Producer (Render — FastAPI)
Routes (all under `/v1`, plus a legacy `/api/*` router kept for migration):

| Endpoint | Purpose |
|---|---|
| `POST /v1/auth/register`, `/login` | Supabase Auth; returns access+refresh tokens |
| `POST /v1/analysis/jobs` | **Cache-first dispatch** → `200 hit` or `processing` + `task_id` |
| `GET  /v1/analysis/jobs/{id}/stream` | **SSE** progress stream |
| `GET  /v1/analysis/jobs/{id}` | Fetch a job's result by `task_id` |
| `GET  /v1/stocks/{ticker}/sentiment` | Latest completed result by ticker |
| `GET  /v1/stocks/{ticker}/chart` | Price history (all periods) |
| `GET/POST/DELETE /v1/users/watchlist` | Watchlist CRUD (**auth-gated**) |
| `GET /health` (+ `HEAD`) | Liveness probe for Render |

- **Stateless** → horizontally scalable behind a load balancer.
- **CORS:** env-driven allowlist (`ALLOWED_ORIGINS`) + a regex that always permits
  `*.vercel.app` and `localhost`, with `allow_credentials=False` (auth is Bearer, not
  cookies). Tolerates quoted/trailing-slash env values.
- **Auth dependency** validates the JWT via `supabase.auth.get_user(token)` (also
  confirms non-revocation), injected with FastAPI `Depends`.

### 5.3 Broker / Cache (Upstash Redis)
One Redis instance plays **three roles**:
1. **Task queue** — TaskIQ `ListQueueBroker` (a Redis list drained with `BRPOP`).
2. **Pub/Sub backplane** — channel `logs:{task_id}` carries progress + terminal
   sentinels from worker → API → browser.
3. **Cache** — see §9.

Must be reached over **`rediss://` (TLS)**; the same URL is used by API and worker.

### 5.4 ML Worker / Consumer (GCP Compute Engine — TaskIQ)
Single TaskIQ task `analyze_sentiment_task(ticker)`; pipeline:

1. `status → running`
2. **Scrape Reddit** via public `reddit.com/search.json` (+ per-post comments;
   `time.sleep(1)` between posts to respect throttling).
3. **Scrape Yahoo** via `yf.Search` for article URLs, then `requests` +
   BeautifulSoup to extract article body text.
4. **FinBERT** sentiment over all collected texts (batched 16, `max_length=512`,
   CPU inference).
5. **Groq** AI summary (Llama 3.3) — **non-fatal**: failure returns `""`.
6. **Collect sources** (de-duplicated Reddit/Yahoo `{source,title,url}`, cap 25).
7. **Persist**: upsert result to Supabase `analysis_jobs` **and** cache by ticker.
8. Publish terminal `DONE`.

The whole pipeline is wrapped in `try/except`: on any failure it sets
`status=failed` and publishes a parseable error event + the `ERROR` sentinel, so the
client fails fast instead of hanging.

- **Memory-capped** (4 GB) and concurrency-limited to prevent OOM.
- **Heavy deps lazy-imported** inside the task so the module loads cheaply.
- Runs **CPU-only torch** (see §11) under `docker-compose.prod.yml` with a restart
  policy / systemd for durability.

### 5.5 Database / Auth (Supabase)
- **`analysis_jobs`** (`id` = TaskIQ `task_id` PK, `ticker`, `status`
  [pending|running|completed|failed], `result` JSONB, `created_at`, `updated_at` +
  auto-update trigger). Indexed on `(ticker, status, created_at desc)` for the
  cache-first recency lookup. RLS: world-readable, service-role writes.
- **`watchlist_items`** (`id` uuid, `user_id` → `auth.users`, `ticker`, `added_at`,
  `unique(user_id, ticker)`). **RLS** restricts read/write to the owning user.
- **Auth** via Supabase Auth (JWT). The API uses the **anon key** for auth ops and
  the **service-role key** for server-side DB writes (bypasses RLS; correctness then
  depends on filtering by the validated `user.id`).
- The app talks to Postgres exclusively through **PostgREST** (`supabase-py`), so DB
  connection pooling is not on the critical path today.

---

## 6. Key data flows

### 6.1 Analysis (cache-first dispatch + streaming)
```
Browser ── POST /v1/analysis/jobs {ticker} ──► API
   API: validate ticker (400 if junk)
        cache hit?  ── yes ─► 200 {status:"hit", data}           (instant, no worker)
        recent (<15m) completed job in Supabase? ── yes ─► 200 hit (re-warm cache)
        else: AsyncKicker.kiq(ticker) → enqueue; upsert pending row
              ── 202 {status:"processing", task_id}
Browser ── GET /v1/analysis/jobs/{task_id}/stream ──► API (SSE)
   API subscribes Redis `logs:{task_id}`
Worker (pulled the job): publishes {"step":...} events  ──► Redis pub/sub ──► API ──► Browser
   ... "Scraping Reddit…", "FinBERT batch 2/5…", "Caching results…" ...
Worker: persist result; publish "DONE"  (or on failure: error event + "ERROR")
Browser: on DONE → GET /v1/analysis/jobs/{task_id} → render grade + summary + sources
         on ERROR/timeout → show error
```

The **cache-first** step is what makes the system fast and cheap: popular/recent
tickers never hit the worker at all.

### 6.2 Streaming detail (SSE over a Redis pub/sub backplane)
The browser cannot reach the GCP worker, and any of N stateless API instances might
serve the stream. So the worker **publishes** progress to `logs:{task_id}` and the
**API instance the client is connected to subscribes** and relays via SSE. The API:
- forwards each message as `data: …`,
- ends the stream on `DONE` (success) or `ERROR` (failure) sentinels,
- sends a `: keepalive` **heartbeat every 15 s** (proxy timeout protection),
- enforces a **120 s hard timeout** (emits a terminal failure if exceeded).

Two clocks (last-real-message vs last-heartbeat) are tracked separately so the
heartbeat can't keep resetting the hard timeout.

### 6.3 Chart, watchlist, auth
- **Chart:** `GET /chart` returns all 7 periods at once (each cached independently
  with a tiered TTL), with NaN/Inf scrubbed and `auto_adjust=True` history.
- **Watchlist:** auth-gated CRUD; the "Save to list" button and sidebar both call it.
- **Auth:** register/login → Supabase → tokens stored client-side; protected routes
  gated by `ProtectedRoute`.

---

## 7. Data model (DDL summary)
```sql
analysis_jobs(
  id text primary key,                 -- TaskIQ task_id
  ticker text not null,
  status text not null default 'pending',  -- pending|running|completed|failed
  result jsonb,                        -- full SentimentResult blob
  created_at timestamptz, updated_at timestamptz)
index (ticker, status, created_at desc)

watchlist_items(
  id uuid pk default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  ticker text not null, added_at timestamptz,
  unique(user_id, ticker))             -- RLS: owner-only
```
`result` (the cached/persisted SentimentResult) contains: `positive/negative/neutral`
counts, `average_*_score`, `verdict`, **`grade`**, `weighted_score`, `article_count`,
`ai_summary`, and **`sources[]`**.

---

## 8. The sentiment model
- **FinBERT** (`ProsusAI/finbert`) classifies each text → {positive, negative,
  neutral} with a confidence; processed in **batches of 16**, truncated to 512 tokens.
- Aggregate **weighted score** ∈ [−1, +1]:
  `weighted = (Σpos·avg_pos − Σneg·avg_neg) / total`.
- **5-tier grade**: `≥0.35 Strong Buy · ≥0.10 Buy · ≥−0.10 Hold · ≥−0.35 Sell · else
  Strong Sell`.
- **AI summary**: Groq `llama-3.3-70b-versatile` via the OpenAI-compatible endpoint
  (called with `requests`), ~5 KB prompt (counts + grade + 15 capped source snippets),
  **one call per uncached analysis**, fail-soft (returns `""` so the UI hides the panel).

---

## 9. Caching strategy
**Cache-first, TTL-based expiry** (not application-level LRU). Every write uses
`SETEX` (key + per-key TTL); Redis auto-expires.

| Key | Contents | TTL |
|---|---|---|
| `cache:{TICKER}` | sentiment result | 15 min |
| `stock:{TICKER}:{period}` | chart series | tiered: 1D 5 m · 1M 1 h · 6M/YTD 6 h · 1Y/5Y/10Y 24 h |
| `tickervalid:{TICKER}` | existence check | 24 h (exists) / 1 h (not) |
| `stockname:{TICKER}` | company name | 7 days |
| `db:{task_id}` | Supabase-down fallback result | *(no TTL — known minor leak)* |
| `logs:{task_id}` | pub/sub progress channel | ephemeral |

**TTL vs LRU:** TTL handles *freshness* (stock data goes stale); a Redis
`maxmemory-policy` (recommended `volatile-lru`, **not** `allkeys-lru` because the
durable task queue shares the instance and must never be evicted) is the *capacity*
safety valve. At current scale the working set is a few MB, so TTL alone suffices.

---

## 10. Fault tolerance & graceful degradation
The system is built to survive flaky third parties:

1. **Scraper failures** (Reddit `403`, Yahoo throttle) → scrapers catch and return
   `[]`. The job still completes with whatever data it got (degraded, not broken).
2. **Worker crash / poison job** → `try/except/finally` marks `status=failed` and
   publishes the `ERROR` sentinel so the client fails fast (no 2-minute hang).
3. **Supabase write failure** → fall back to writing the result to Redis (`db:{id}`).
4. **LLM failure** (e.g. quota) → summary returns `""`; the panel is hidden, the job
   still succeeds. Raw provider errors are **never** shown to users.
5. **Stream timeout** → terminal failure event (not an infinite spinner).

### 10.3 A note on correctness: broker-accurate gain/loss
The chart header's gain/loss is **period-aware**: **1D** uses the backend's
*previous-close*-based daily change (matches a broker's "today", including the
overnight gap); **longer ranges** use the visible range (first point → current) on
**split/dividend-adjusted** prices (`auto_adjust=True`), so post-split names like NVDA
show correct multi-year returns.

---

## 11. War stories (real bugs & the fixes — great presentation material)
These demonstrate depth far better than the happy path.

1. **CORS-less 500 → "failed to fetch."** The chart endpoint threw an *unhandled*
   exception **during JSON serialization** (after the handler returned), which
   **bypasses FastAPI's CORS middleware** — so the browser saw a header-less 500 and
   reported "failed to fetch" (while sentiment worked). *Lesson: errors thrown in
   response rendering don't get CORS headers; an unhandled 500 ≠ a handled error.*
2. **yfinance NaN crashing serialization.** On a rate-limited datacenter IP, yfinance
   returned price history with `NaN`; Starlette's renderer uses `allow_nan=False`, so
   the response crashed. Worse, **older builds had cached the NaN** (JSON round-trips
   `NaN` as `float('nan')`), so even fixing the fresh path failed until cached series
   were scrubbed too. *Lesson: sanitize at the serialization boundary AND on cache read.*
3. **Gemini free-tier `limit: 0`.** AI summaries were always blank; the key was valid
   but the region's free tier grants **zero** quota. **Switched to Groq** (free,
   datacenter-friendly, OpenAI-compatible) via a ~20-line provider swap — same prompt,
   same fail-soft contract. *Lesson: provider-agnostic boundaries make swaps cheap.*
4. **`REDIS_URL` outage.** The worker crash-looped (`Connection closed by server`)
   and the API 500'd because the env value was `"redis://…"` — **quoted** (so it
   wouldn't parse) **and plaintext** (Upstash is TLS-only → `rediss://`). *Lesson:
   validate/normalize secrets at boot; TLS scheme matters.*
5. **CUDA bloat / disk-full build.** `torch>=2.1` resolved to a wheel pulling ~2.5 GB
   of NVIDIA CUDA libs onto a CPU-only VM → `No space left on device`. Fixed by
   installing **CPU-only torch** from PyTorch's CPU index. *Lesson: pin the runtime you
   actually run on.*
6. **Datacenter IP rate-limiting** is the persistent systemic risk — Reddit `403`,
   Yahoo "Too Many Requests" — which is *why* the durable fix is an ingestion/precompute
   model + paid data APIs (see §14).

A small per-edge diagnostic (`scripts/diagnose.sh`) probes API → Redis → Worker →
Supabase **in dependency order** so a silent failure localizes to a specific broken
connection — invaluable in a multi-service system.

---

## 12. Trade-offs & design choices
| Decision | Chose | Why / Pro | Con / Cost |
|---|---|---|---|
| Web vs ML coupling | **Separate processes (producer/consumer)** | Fault isolation; independent scaling; tiny API image | More moving parts; eventual consistency |
| Real-time transport | **SSE** | Simple, unidirectional fits progress; auto-reconnect; plain HTTP | One-way; HTTP/1.1 conn limits |
| Worker→client path | **Redis pub/sub backplane** | Any API instance can relay; worker stays unreachable/internal | Fire-and-forget: late subscribers miss early msgs (mitigated by final fetch) |
| Job queue | **TaskIQ `ListQueueBroker` (Redis)** | Zero extra infra; already have Redis | No durability/DLQ; `BRPOP` quirks on managed Redis |
| Data freshness | **Cache-first, TTL** | Most requests instant; shields the worker | Staleness (≤15 min); no LRU until needed |
| Data acquisition | **On-demand scraping (free)** | Simple; no storage/ingestion | Latency + rate-limit fragility on datacenter IPs |
| Market data | **yfinance (free)** | $0 | Unreliable from datacenters (the chart saga) |
| DB/Auth | **Supabase (BaaS)** | Auth + Postgres + RLS out of the box; fast to build | Vendor lock-in; REST not raw SQL |
| Inference | **FinBERT on CPU** | Cheap, no GPU | ~25 s/job; doesn't scale on its own |
| LLM | **Groq free tier** | Free, fast, OpenAI-compatible | Rate limits; model constraints |
| Worker shape | **One monolithic task** | Simple to reason about | A slow/failed stage blocks the whole; stages can't scale independently |

---

## 13. Testing & ops
- **Tests:** backend `pytest` (validators, worker failure path, source collection,
  auth error discrimination, chart NaN-scrub + periods); frontend `vitest` +
  Testing Library (api 401 interceptor, ticker/jwt utils, SourcesList, StockChart
  periods + period-aware gain/loss, SaveToListButton). TDD/“Prove-It” for bug fixes.
- **Deploy:** Vercel (frontend, auto), Render (API Docker, auto, `/health` probe),
  GCP VM (worker, manual `git pull` + `docker compose ... up -d --build worker`).
  Full guide in `docs/DEPLOYMENT.md`.
- **Diagnostics:** `scripts/diagnose.sh` for per-edge connectivity.

---

## 14. Scaling to 4M users / 300K DAU (Wealthsimple-scale)

**The load:** ~300K DAU × ~5 analyses + ~50 reads ≈ **1.5M analyses/day** (~150–200/s
at market open) and ~**15M reads/day** (~2,000/s peak). At ~25 s/CPU-job, 200
analyses/s naïvely needs ~5,000 cores — absurd.

**The insight that changes everything:** like Wealthsimple, ~99% of traffic
concentrates on a few hundred popular tickers. So **flip from compute-on-request to
compute-on-ingest** — continuously ingest + score the tracked universe, and make user
requests **pure cache reads**. The architecture is already cache-first; this is its
natural endpoint.

**Phased plan**
- **Phase 0 (→10K DAU):** swap to real data APIs (Finnhub/Twelve Data/Polygon for
  prices, official Reddit/News APIs) — kills the 403/NaN class; add observability
  (Sentry/metrics/traces) and a secrets manager; turn on scheduled pre-warming of the
  top ~500 tickers; autoscale ≥2 workers + DLQ.
- **Phase 1 (10K→100K):** **ingestion service** + **GPU-batched FinBERT** computing
  sentiment on a schedule → near-100% cache hits; Redis Cluster; CDN (Cloudflare) in
  front of chart/sentiment JSON; Postgres read replicas + partitioning; API on
  autoscaling Cloud Run/ECS/k8s.
- **Phase 2 (100K→300K+):** **Kafka/SQS** broker (durable, partitioned, replayable);
  real-time tier (managed Ably/Pusher or scaled SSE/WS) — but most analyses are now
  instant cache hits, so concurrent streams collapse; dedicated GPU inference service;
  multi-region; data warehouse for the sentiment time-series.
- **Phase 3:** SLOs/error budgets, load + chaos testing, WAF/DDoS, audit logs, SOC2.

**Target steady state**
```
Cloudflare CDN/WAF ─ Vercel ─ API (Cloud Run, autoscaled, stateless)
   ├─ Redis Cluster (cache + pub/sub)
   ├─ Postgres (replicas, partitioned)
   └─ Kafka ─► GPU inference fleet ◄─ Ingestion workers ◄─ Market/News APIs
        (precomputed sentiment & charts served from cache)
Real-time tier ─ only for rare live/cold analyses
```
The two cheapest, highest-impact moves: **(1) real data APIs** and **(2) scheduled
pre-warming** — they fix the NFR gaps *and* set up the precompute model scaling needs,
without rewriting the app.

---

## 15. Known limitations (be honest in the interview)
- Single worker = SPOF; no autoscaling yet.
- Datacenter IP rate-limiting degrades data quality (the systemic risk).
- SSE 120 s hard timeout exceeds the 60 s E2E NFR; scraping latency is the bottleneck.
- Pub/sub is fire-and-forget → a late SSE subscriber misses early messages (mitigated
  by the cache-first + final-result fetch).
- `db:{task_id}` fallback key has no TTL (minor unbounded growth in a Supabase outage).
- Ticker validation regex rejects some valid symbols (>5 chars, certain ETFs/indices).
- Observability was a real gap during development (Render logs were the only window).

---

## 16. Interview talking points (lead with these)
1. **"The architecture is dictated by two hostile realities — slow ML and flaky data
   sources — and a hard availability requirement."** Then show the producer/consumer
   split as the answer to availability/fault-isolation.
2. **The decoupling mechanics:** API enqueues by task name (`AsyncKicker`), never
   imports ML; separate dependency images; worker is internal/unreachable.
3. **Real-time without coupling:** SSE relayed off a **Redis pub/sub backplane**, with
   sentinels, heartbeats, and dual-clock timeout — and *why* pub/sub (any API instance
   can serve any stream).
4. **Cache-first as the scalability lever:** explain how it shields the worker today
   and becomes **precompute-on-ingest** at Wealthsimple scale (the 99%-popular-ticker
   insight).
5. **A war story for depth:** the CORS-less-500 (serialization errors bypass CORS) or
   the NaN-in-cache bug — both show debugging rigor and understanding of the full
   request lifecycle.
6. **Trade-offs you'd revisit at scale:** on-demand scraping → ingestion pipeline;
   Redis list → Kafka; CPU FinBERT → GPU batch; yfinance → paid market data.

---

*Companion docs:* `docs/DEPLOYMENT.md` (full deploy runbook) · `scripts/diagnose.sh`
(per-edge connectivity diagnostic).
