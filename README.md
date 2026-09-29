# Candorify

**Read your medical bills before you pay.**

Candorify helps patients review itemized medical bills, surfacing **potential discrepancies to review** — duplicate charges, arithmetic errors, and quantity errors — and translating opaque billing codes into plain English (and other languages).

> ⚠️ **Disclaimer:** Candorify identifies *possible* billing discrepancies for your review. It does **not** verify charges, confirm errors, or guarantee savings. It is **not** a substitute for a billing auditor, advocate, or legal/financial advisor. Nothing is confirmed until the provider or insurance agrees. Acting on flagged items is your own responsibility. The prototype uses **synthetic bills only** — no real patient data.

---

## What's in this repo

| Area | Path | Stack |
|------|------|-------|
| Backend API | `backend/` | Python, FastAPI, SQLite (SQLAlchemy) |
| Website | `frontend/` | Vanilla HTML / CSS / JS |
| Mobile app | `mobile/` | Cross-platform (Capacitor-wrapped web) |
| Synthetic data | `backend/app/generator/` | Python + labeled answer keys |
| Check engine | `backend/app/checks/` | Python |
| Translation | `backend/app/translation/` | NLM Clinical Tables + LibreTranslate + offline fallback |
| Medicare benchmark | `backend/app/benchmark/` | CMS Physician Fee Schedule + offline fallback (paid) |
| Templates | `backend/app/templates_engine/` | Python |
| Payments | `backend/app/payments/` | Stripe (test mode) |

## Core features

- **Synthetic bill generator** — realistic itemized bills with injectable errors and a ground-truth answer key for accuracy testing.
- **Check engine** — duplicate / arithmetic / quantity detection. Reports precision, recall, false-positive and false-negative rates against the answer key. Target: ≥95% recall, <5% false-positive rate.
- **Translation** — billing codes → plain English → other languages. Every line explained.
- **Template engine** — editable "request itemized bill" and "dispute a charge" letters.
- **Tiered access** — free tier (request bill + duplicate/arithmetic checks); paid tier (line-by-line translation, Medicare rate comparison, dispute letters).
- **Payments** — Stripe test-mode checkout.
- **Privacy** — one-tap deletion, auto-delete after a retention window, data minimization.

## Quick start

See [`docs/SETUP.md`](docs/SETUP.md).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `frontend/index.html` (served at `http://localhost:8000/`).
