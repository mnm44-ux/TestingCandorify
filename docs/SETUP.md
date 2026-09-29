# Candorify — Setup & Run

## Prerequisites
- Python 3.10+ (backend)
- Node.js 18+ (only for the mobile app build)

## 1. Backend + Website (one process serves both)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional; sensible dev defaults exist
uvicorn app.main:app --reload
```

Open **http://localhost:8000/** — the FastAPI app serves the website from
`../frontend` and the JSON API under `/api/*`.

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

### Run the tests
```bash
cd backend
pip install -r requirements-dev.txt   # includes pytest (prod uses requirements.txt)
pytest -q
```

### Measure accuracy against the labeled synthetic set
```bash
# Rebuild the labeled dataset CSVs (bills + answer key):
python -m scripts.build_dataset 100
# Or hit the scoring endpoint once the server is running:
curl -X POST "http://localhost:8000/api/bills/score?num_bills=100"
```
Target: recall ≥ 95%, false-positive rate < 5%.

### Retention sweep (scheduled deletion)
```bash
python -m scripts.retention_sweep   # cron this daily
```

## 2. Enabling the real external services (optional)

By default the prototype runs fully offline (bundled code dataset + mock
payments). To use the real providers, set these in `.env`:

- **Translation:** `CANDORIFY_TRANSLATION_OFFLINE_ONLY=false`
  (uses NLM Clinical Tables for code lookup and LibreTranslate for language
  translation).
- **Payments:** `CANDORIFY_PAYMENTS_MOCK_MODE=false` plus your Stripe test keys
  (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_PRICE_ID_PAID`,
  `STRIPE_WEBHOOK_SECRET`).

## 3. Mobile app (iOS + Android)

See [`../mobile/README.md`](../mobile/README.md). In short:

```bash
cd mobile
npm install
export CANDORIFY_API_BASE="https://your-deployed-api"
npm run build
npm run add:android    # or add:ios
npm run open:android   # or open:ios
```

## Project layout

```
backend/    FastAPI app, SQLite, generator, check engine, translation,
            templates, payments, tests, dataset + ops scripts
frontend/   Vanilla HTML/CSS/JS website (also the mobile UI source)
mobile/     Capacitor wrapper -> native iOS + Android
docs/       Setup + legal/privacy
```
