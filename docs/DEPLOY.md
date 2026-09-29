# Deploying Candorify

The API and website ship as a single container (see `Dockerfile`). The image
serves the JSON API under `/api/*` and the static site at `/`.

## Option A — Render (blueprint, recommended)

1. Push this repo to GitHub (already done).
2. In the [Render dashboard](https://dashboard.render.com/): **New + → Blueprint**,
   select this repo. Render reads `render.yaml` and creates the web service.
3. First deploy runs with safe offline defaults (mock payments, offline
   translation/benchmark) so it comes up green immediately.
4. Visit the service URL — `/api/health` should return `{"status":"ok"}`.

### Going live with external services

Set these in **Render → your service → Environment** (as secret env vars — never
commit them), then redeploy:

| Purpose | Variable | Value |
|---------|----------|-------|
| **AI (Gemini) for translation + email drafting** | `CANDORIFY_LLM_API_KEY` | your free Gemini key ([get one, no card](https://aistudio.google.com/app/apikey)) |
| Fallback live code lookup + translation | `CANDORIFY_TRANSLATION_OFFLINE_ONLY` | `false` |
| Live Medicare rates | `CANDORIFY_BENCHMARK_OFFLINE_ONLY` | `false` |
| Real Stripe | `CANDORIFY_PAYMENTS_MOCK_MODE` | `false` |
| Stripe secret key | `CANDORIFY_STRIPE_SECRET_KEY` | `sk_test_…` / `sk_live_…` |
| Stripe publishable key | `CANDORIFY_STRIPE_PUBLISHABLE_KEY` | `pk_test_…` |
| Stripe price (paid plan) | `CANDORIFY_STRIPE_PRICE_ID_PAID` | `price_…` |
| Stripe webhook secret | `CANDORIFY_STRIPE_WEBHOOK_SECRET` | `whsec_…` |
| LibreTranslate key (optional) | `CANDORIFY_LIBRETRANSLATE_API_KEY` | your key |

For Stripe webhooks, point Stripe at `https://<your-service>/api/payments/webhook`.

### Database

On the **free tier**, Render does not support persistent disks, so the blueprint
uses an **ephemeral SQLite** database that resets when the service restarts or
sleeps. That is fine for a synthetic-data prototype/demo.

For durable data, either upgrade the plan and add a `disk:` block back to
`render.yaml` (mount at `/app/backend/data` and point `CANDORIFY_DATABASE_URL`
at it), or — recommended for real traffic — create a **managed Postgres** on
Render and set:

```
CANDORIFY_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

(Add `psycopg[binary]` to `backend/requirements.txt` when using Postgres.)

## Option B — Any Docker host (Fly.io, AWS, GCP, a VM…)

```bash
# Build (run from the repo root so both backend/ and frontend/ are in context):
docker build -t candorify .

# Run:
docker run -p 8000:8000 \
  -e CANDORIFY_SECRET_KEY="$(openssl rand -hex 32)" \
  candorify
# open http://localhost:8000/
```

Pass any of the env vars from the table above with `-e`. The container reads
`$PORT` if the host sets one (otherwise defaults to 8000).

## Option C — Local (no Docker)

See [`SETUP.md`](SETUP.md).

## Scheduled retention sweep

Run the deletion sweep on a schedule (e.g. Render Cron Job or system cron):

```bash
cd backend && python -m scripts.retention_sweep
```

## Health check

`GET /api/health` returns app status and whether offline/mock modes are active —
useful for load-balancer health checks and for confirming your env vars took
effect after enabling live services.
