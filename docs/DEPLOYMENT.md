# Stocker — End-to-End Deployment Guide

This guide deploys the full Stocker stack across five providers. **Order matters** —
each later step needs URLs/keys produced by an earlier one:

```
Supabase (DB + Auth) → Upstash (Redis) → Render (API) → GCP VM (Worker) → Vercel (Frontend)
```

One shared `.env` feeds both backend services (API + Worker). The frontend gets a single
build-time Vite variable. **Never commit `.env`** — it is gitignored; `.env.example` is the
tracked template.

---

## 0. Secrets you will collect

| Variable | Source | Used by |
|---|---|---|
| `SUPABASE_URL` | Supabase → Settings → API | API + Worker |
| `SUPABASE_KEY` | Supabase anon/public key | API (auth) |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key (server-only) | API + Worker (DB writes) |
| `REDIS_URL` | Upstash (`rediss://…`, TLS) | API + Worker (queue, pub/sub, cache) |
| `GROQ_API_KEY` | console.groq.com (free tier) | Worker (AI summary) |
| `ALLOWED_ORIGINS` | Your Vercel URL (after step 5) | API (CORS) |
| `VITE_API_URL` | Your Render URL (after step 3) | Frontend (build-time) |

---

## 1. Supabase — Database + Auth

1. **Create project** at [supabase.com](https://supabase.com) → New Project. Pick a region
   close to your **Render** region (the API ↔ Supabase round-trips dominate request latency).
2. **Run the schema:** Dashboard → SQL Editor → New query → paste the contents of
   [`backend/migrations/001_initial_schema.sql`](../backend/migrations/001_initial_schema.sql)
   → Run. This creates `analysis_jobs`, `watchlist_items`, RLS policies, and the
   `updated_at` trigger.
3. **Auth config:** Authentication → Providers → enable **Email**.
   - For the first E2E pass, **disable "Confirm email"** (Authentication → Sign In / Providers)
     so `sign_up` returns a session immediately. The code already handles the
     confirmation-required path, but disabling it removes a manual step during testing.
   - **Re-enable email confirmation for production.**
   - **URL Configuration (critical):** Authentication → URL Configuration →
     - **Site URL** must match where the frontend actually runs:
       `http://localhost:8080` for local Vite dev (NOT `:3000`), or your Vercel URL in prod.
     - **Redirect URLs:** add `http://localhost:8080/**` and `https://<your-app>.vercel.app/**`.
     - The confirmation email links back to the Site URL with the session in the URL hash
       (`/#access_token=…&type=signup`). The frontend's `AuthProvider` parses that hash on load
       and establishes the session — but only if the link points at the running app, so a wrong
       Site URL (e.g. `:3000`) lands the user on a dead page.
4. **Collect keys:** Settings → API →
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_KEY`
   - **service_role** → `SUPABASE_SERVICE_KEY` (server-side only — never ship to the browser)
5. **Connection pooling — note:** Stocker talks to Supabase exclusively through the
   **PostgREST client** (`supabase-py`), not raw Postgres connections, so PgBouncer/pooler
   tuning is **not on the critical path**. RLS is enabled and the backend uses the
   service_role key for writes — that is what matters. Only revisit pooling if you later add
   direct `psql`/SQLAlchemy access, in which case use the **Transaction pooler** string
   (port `6543`) for serverless/short-lived connections.

---

## 2. Upstash — Redis (queue + pub/sub + cache)

1. **Create database** at [upstash.com](https://upstash.com) → Redis. Choose a region close
   to your **Worker** (queue throughput is worker-bound). Enable **TLS**.
2. **Connection string:** copy the `rediss://default:<password>@<host>:<port>` URL →
   `REDIS_URL`. The **same** URL serves all three roles — the TaskIQ queue, the `logs:*`
   pub/sub channels for SSE, and the `cache:*` keys.
3. **Use the TCP/TLS endpoint (`rediss://`), not the REST URL.** `taskiq-redis` and
   `redis.asyncio` need RESP/TCP; the REST endpoint will not work for the queue or pub/sub.
4. **Capacity:** each active SSE stream holds one long-lived subscriber connection. The free
   tier caps concurrent connections and daily commands — size the plan to your expected number
   of concurrent analyses.

---

## 3. Render — FastAPI API Gateway (Producer)

1. New → **Web Service** → connect the repo → **Runtime: Docker**.
   - **Dockerfile path:** `backend/Dockerfile.api`
   - **Root Directory:** `backend` (so `COPY` paths resolve)
2. **Start command:** none required — `Dockerfile.api` already runs
   `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`, and Render injects `PORT`.
3. **Environment variables:** add `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`,
   `REDIS_URL`, `GROQ_API_KEY`, and (after step 5) `ALLOWED_ORIGINS`. Do **not** upload `.env`.
4. **Health check path:** `/health` (the app serves `GET`/`HEAD /health`, matching Render's
   HEAD probes).
5. **Instance size:** the API is lightweight — `requirements-api.txt` excludes torch/ML deps,
   so the smallest paid instance is fine. Note: Render free tier **cold-starts**; keep
   `PREWARM_ON_STARTUP` off in prod until you explicitly want the popular-ticker pre-warm
   (it enqueues several heavy jobs on each boot).

---

## 4. GCP VM — TaskIQ ML Worker (Consumer)

1. **Provision:** Compute Engine → **e2-standard-2** (2 vCPU, **8 GB RAM**), Ubuntu 22.04 LTS,
   20 GB+ disk.
   - FinBERT + torch hold ~1.5 GB resident plus batch tensors (batch size 16). `e2-medium`
     (4 GB) is the floor and risks OOM under concurrency; the compose memory limit is already
     4 GB, so an 8 GB host gives headroom.
2. **Install Docker + Compose:**
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER && newgrp docker
   sudo systemctl enable docker        # start on boot
   ```
3. **Get code + secrets:**
   ```bash
   git clone <repo-url> stocker && cd stocker
   # create .env with the SAME values as Render, PLUS the Upstash REDIS_URL
   # (the worker connects to Upstash, NOT a local Redis)
   chmod 600 .env
   ```
4. **Run the worker** via the production compose (no local Redis, no hot-reload):
   ```bash
   docker compose -f docker-compose.prod.yml up -d worker
   ```
   `Dockerfile.worker` runs `taskiq worker tasks:broker`; `restart: unless-stopped` keeps it
   alive across crashes and reboots.
5. **Keep it running as a daemon — two valid options:**

   **Option A (recommended, compose-native):** the `restart: unless-stopped` policy plus
   `systemctl enable docker` already survives crashes and reboots. Preferred over
   `tmux`/`screen`, which do **not** survive a reboot or a process crash.

   **Option B (systemd wrapper, for OS-level supervision):**
   ```ini
   # /etc/systemd/system/stocker-worker.service
   [Unit]
   Description=Stocker TaskIQ Worker
   Requires=docker.service
   After=docker.service network-online.target

   [Service]
   WorkingDirectory=/home/<user>/stocker
   ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up worker
   ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload && sudo systemctl enable --now stocker-worker
   ```
6. **Concurrency guard (OOM prevention):** `ListQueueBroker` processes serially per worker by
   default. Keep a single worker process on the 8 GB box. If you scale out later, cap with
   `taskiq worker tasks:broker --max-async-tasks 1` so multiple FinBERT batches never load at
   once.
7. **Networking:** the worker only makes **outbound** connections (Upstash, Supabase,
   Reddit/Yahoo, Groq). No inbound firewall rules needed — leave default-deny ingress.

---

## 5. Vercel — Frontend

1. New Project → import the repo → **Root Directory:** `frontend` → Framework preset **Vite**.
   - Build command: `npm run build` · Output directory: `dist`
2. **Environment variable:** `VITE_API_URL` = your Render URL
   (e.g. `https://stocker-api.onrender.com`). Vite **inlines env at build time** — redeploy
   after changing it.
3. **SPA routing:** react-router needs a catch-all rewrite or deep links 404 on refresh. Add
   `frontend/vercel.json`:
   ```json
   { "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
   ```
4. **Close the CORS loop:** copy the deployed Vercel URL into Render's `ALLOWED_ORIGINS`, then
   redeploy the API.

---

## 6. End-to-end smoke test

1. `curl https://<render-url>/health` → `{"status":"ok"}`
2. Open the Vercel URL → Register → land an authenticated session.
3. Search `AAPL`:
   - chart loads from `/v1/stocks/AAPL/chart`
   - SSE log lines stream (`Scraping Reddit…` → `FinBERT…` → done)
   - sentiment + AI summary render
4. **Negative paths** (these exercise the hardening fixes):
   - bad login → clear error toast (no silent form-clear)
   - junk ticker `ASDFGH` → `400` + inline message (not a hung spinner)
   - kill the worker mid-job → fast, explicit error (not a 2-minute hang)

---

## Environment variable reference

See [`.env.example`](../.env.example) for the canonical backend template. Summary:

```bash
# Backend (Render API + GCP Worker) — identical values on both
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<anon-public-key>
SUPABASE_SERVICE_KEY=<service-role-key>
REDIS_URL=rediss://default:<password>@<host>:<port>
GROQ_API_KEY=<groq-api-key>            # free key from console.groq.com
ALLOWED_ORIGINS=https://<your-app>.vercel.app   # API CORS allowlist
PREWARM_ON_STARTUP=false                         # popular-ticker pre-warm (off by default)

# Frontend (Vercel) — build-time
VITE_API_URL=https://<your-api>.onrender.com
```
