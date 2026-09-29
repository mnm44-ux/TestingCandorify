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

## Uploaded bills (real PDFs)

- **Local parsing + PII stripping.** Uploaded PDFs are parsed on the server; the
  raw bytes are read in memory and never written to disk. Personal identifiers
  (name, address, sex, birthdate, phone, email, SSN, MRN, account number) are
  removed on a best-effort basis before any external call.
- **Hybrid AI translation.** Only medical content (codes, descriptions, provider
  name, amounts) is sent to Google (Gemini) for translation. This is disclosed in
  the Terms the user must accept at signup. Redaction is best-effort, not a guarantee.
- **Original never modified.** A separate, newly generated annotated PDF is
  produced for the user to download and share.
- **Ephemeral.** Uploaded bill data (`is_synthetic = false`) is permanently
  deleted when the user finishes the review (survey submit) or by the retention
  sweep. Only non-identifying performance stats are retained (`SurveyStat`).

## Synthetic demo data

- The demo bill generator produces synthetic itemized bills (`is_synthetic = true`)
  with no real patient data, used for trying the app and for accuracy testing.
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
