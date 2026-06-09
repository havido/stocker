#!/usr/bin/env bash
#
# Stocker connectivity diagnostic.
# Probes each EDGE of the distributed system independently, in dependency order,
# so a silent failure shows up as a specific broken connection rather than a
# vague "it doesn't work".
#
# Usage:
#   ./scripts/diagnose.sh                         # local stack (API on :8000)
#   API_URL=https://stocker-api.onrender.com ./scripts/diagnose.sh   # deployed
#
# Optional env (falls back to ./.env if present):
#   API_URL        base URL of the Render/API gateway   (default http://localhost:8000)
#   REDIS_URL      Upstash/Redis URL for a direct probe (optional)
#   SUPABASE_URL   Supabase project URL for a direct probe (optional)
#   PROBE_TICKER   real ticker for the full queue->worker test (default AAPL)

set -u
API_URL="${API_URL:-http://localhost:8000}"
PROBE_TICKER="${PROBE_TICKER:-AAPL}"

# Load .env for REDIS_URL / SUPABASE_URL if not already set.
if [ -f ".env" ]; then
  # shellcheck disable=SC2046
  export $(grep -E '^(REDIS_URL|SUPABASE_URL)=' .env | xargs -0 2>/dev/null) 2>/dev/null || true
  [ -z "${REDIS_URL:-}" ] && REDIS_URL="$(grep -E '^REDIS_URL=' .env | head -1 | cut -d= -f2-)"
  [ -z "${SUPABASE_URL:-}" ] && SUPABASE_URL="$(grep -E '^SUPABASE_URL=' .env | head -1 | cut -d= -f2-)"
fi

pass=0; fail=0; warn=0
P() { echo "  ✅ $1"; pass=$((pass+1)); }
F() { echo "  ❌ $1"; fail=$((fail+1)); }
W() { echo "  ⚠️  $1"; warn=$((warn+1)); }
hr() { echo "── $1 ──────────────────────────────────"; }

echo "Target API: $API_URL"
echo

# ── EDGE 1: Is the API gateway alive? ────────────────────────
hr "1. API gateway (Render)"
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$API_URL/health" 2>/dev/null)
if [ "$code" = "200" ]; then P "GET /health → 200 (API process up)"
else F "GET /health → ${code:-no response} (API down or wrong URL — check Render logs first; nothing downstream matters until this passes)"; fi

# ── EDGE 2: API → Redis (enqueue path) ───────────────────────
hr "2. API → Redis  (queue + cache)"
resp=$(curl -s --max-time 20 -X POST "$API_URL/v1/analysis/jobs" \
  -H 'Content-Type: application/json' -d "{\"ticker\":\"$PROBE_TICKER\"}" 2>/dev/null)
status=$(printf '%s' "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
TASK=$(printf '%s' "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null)
case "$status" in
  hit)        P "POST analysis → cache HIT (API↔Redis cache working; result already warm)";;
  processing) P "POST analysis → enqueued task_id=$TASK (API↔Redis queue write OK)";;
  *)          F "POST analysis → unexpected: ${resp:0:160} (API can't reach Redis, or validation rejected the ticker)";;
esac

# ── EDGE 3: Redis → Worker (queue drain) ─────────────────────
hr "3. Redis → Worker  (GCP consumer draining the SAME queue)"
if [ -n "$TASK" ]; then
  drained=""
  for i in $(seq 1 12); do
    st=$(curl -s --max-time 10 "$API_URL/v1/analysis/jobs/$TASK" 2>/dev/null \
         | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
    if [ "$st" = "running" ] || [ "$st" = "completed" ]; then drained="$st"; break; fi
    sleep 5
  done
  if [ -n "$drained" ]; then P "job moved to '$drained' → worker IS draining the queue"
  else W "job still 'pending' after 60s → worker NOT consuming. #1 cause: REDIS_URL differs between API and worker (they must be the IDENTICAL Upstash rediss:// string). Also check the worker container is running (docker compose ps)."; fi
else
  W "no task_id from edge 2 (cache hit or enqueue failed) → can't test the drain path this run"
fi

# ── EDGE 4: API → Supabase (auth + DB) ───────────────────────
hr "4. API/Worker → Supabase"
if [ -n "${SUPABASE_URL:-}" ]; then
  scode=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$SUPABASE_URL/auth/v1/health" 2>/dev/null)
  if [ "$scode" = "200" ] || [ "$scode" = "401" ]; then P "Supabase reachable (HTTP $scode — 401 just means 'needs key', TLS/DNS fine)"
  elif [ -z "$scode" ]; then F "Supabase unreachable (timeout/DNS/TLS — if you see CERTIFICATE_VERIFY_FAILED it's usually a proxy/VPN intercepting TLS on your network)"
  else W "Supabase returned HTTP $scode (reachable but unexpected — check SUPABASE_URL)"; fi
else W "SUPABASE_URL not set → skipped (export it or add to .env to probe)"; fi

# ── EDGE 5: Direct Redis probe (optional) ────────────────────
hr "5. Redis direct (optional)"
if [ -n "${REDIS_URL:-}" ] && command -v redis-cli >/dev/null 2>&1; then
  if redis-cli -u "$REDIS_URL" ping 2>/dev/null | grep -qi pong; then P "redis-cli PING → PONG (Redis creds valid from this host)"
  else F "redis-cli PING failed (bad REDIS_URL or network/TLS to Upstash)"; fi
else W "skipped (set REDIS_URL and install redis-cli to probe Redis directly)"; fi

echo
hr "SUMMARY"
echo "  $pass passed, $fail failed, $warn warnings"
[ "$fail" -eq 0 ] && echo "  All tested edges are connected." || echo "  Fix the ❌ edges top-down — an earlier broken edge cascades into later ones."
