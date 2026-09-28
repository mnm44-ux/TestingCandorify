# Candorify — Disclaimer, Privacy & Data Handling

## User disclaimer (shown in-app)

> Candorify identifies **possible** billing discrepancies for your review; it
> does **not** verify charges, confirm errors, or guarantee savings. It is
> **not** a substitute for a billing auditor, advocate, or legal or financial
> advisor. Nothing is confirmed until the provider or insurance agrees. Acting
> on flagged items is your own responsibility.

This text is served live from `GET /api/disclaimer` and rendered on the home
page and footer, so there is a single source of truth.

## Flag language

Every finding produced by the check engine is phrased as a **"potential
discrepancy to review."** Candorify **never** auto-concludes that an error
exists. The user explicitly **confirms** (for follow-up) or **dismisses** each
flag; nothing is marked as a verified error or a guaranteed saving.

## Prototype data policy

- **Synthetic data only.** The prototype generates synthetic itemized bills and
  never ingests real patient data. All bills carry `is_synthetic = true`.
- Because the patient uploads their own bill, this prototype is **not a HIPAA
  covered entity**. This is not legal advice; validate with counsel before
  handling real data.

## Production data-handling design

- **Data minimization.** Store only what is needed to run the checks.
- **Encryption in transit** (HTTPS/TLS) in production deployments.
- **Retention window.** Uploads auto-delete after `CANDORIFY_UPLOAD_RETENTION_DAYS`
  (default 30). The sweep runs via `DELETE`-equivalent logic in
  `POST /api/privacy/sweep` and `scripts/retention_sweep.py` (cron-friendly).
- **One-tap deletion.** `DELETE /api/privacy/me` removes the account and all
  associated bills, line items, flags, and answer keys (DB cascade).
  `DELETE /api/bills/{id}` removes a single bill immediately.
- **No selling or sharing** of user data.

## Future / larger-audience note

Any future employer-facing version will receive **aggregated figures only** and
**never individual records**.

## Payments & PCI

Card data is entered on Stripe's hosted checkout / Stripe.js — Candorify never
sees or stores raw card numbers. Only Stripe customer/subscription identifiers
are persisted.
