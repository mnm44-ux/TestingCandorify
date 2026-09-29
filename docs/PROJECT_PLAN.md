# Candorify — Team Plan & Timeline (Fall 2026)

**Read your medical bills before you pay.**

This plan maps the Candorify product roadmap onto the YWCC Capstone Student
Startup Track sprint calendar. All dates are Eastern Time and taken from the
Fall 2026 guidebook.

---

## Team & core roles

| Person | Role | Owns |
|--------|------|------|
| **Mariz** | Founder / PM / Frontend | Product vision, sprint planning, all 5 PM reports, meeting & decision log, **frontend** (all pages/UI), GitHub cards, customer-discovery lead |
| **Vrajesh** | Backend | FastAPI endpoints, feature logic, integrations (Gemini / Stripe), API contracts |
| **Nathalie** | Database | Schema, migrations, data integrity, caching, retention/deletion, data-model docs |
| **Mathew** | Testing & Research | Test suites, accuracy measurement, QA, customer/competitor research, MDDDE "Evaluate" evidence |

> Everyone also does Scrum, attends coaching, and must be able to explain their own contribution (course requirement).

---

## Sprint calendar → build mapping

| Sprint | Dates | Capstone milestone | Candorify focus |
|--------|-------|--------------------|-----------------|
| **S1** | Sep 29 – Oct 12 | Orientation; **PM Report 1 (Oct 8)** | Foundations: repo, DB, auth, Tauri setup, home page |
| **S2** | Oct 13 – Oct 26 | **Progress review (Oct 13)**; **PM Report 2 (Oct 22)** | Core features working: code lookup, bill upload, logged-out marketing pages |
| **S3** | Oct 27 – Nov 9 | **Midterm demo (Nov 3)**; **PM Report 3 (Nov 5)** | MVP demo-ready: annotated bill generator, translation, subscription tiers |
| **S4** | Nov 10 – Nov 23 | Boot camp (Nov 14); **PM Report 4 (Nov 19)** | Remaining features: templates, treatment comparison, email, reviews; harden |
| **S5** | Nov 24 – Dec 5 | **Pre-final (Dec 1)**; **Showcase (Dec 5)** | Polish, test, docs; near-final |
| **Wrap** | Dec 6 – Dec 13 | **Final package + PM Report 5 (Dec 13)** | Technical handover |

---

## Sprint 1 — Foundations (Sep 29 – Oct 12)
*Requirement: database setup, website "kinda working", Tauri set up.*

| Owner | Tasks | Collaborates with |
|-------|-------|-------------------|
| **Mariz** | Home page; scaffold logged-in vs logged-out shell; set up GitHub Projects board + cards; PM Report 1; run Sprint 1 planning | Vrajesh (auth UI ↔ API contract); all (roles) |
| **Vrajesh** | Login & registration endpoints; session/JWT; wire terms acceptance | Nathalie (User schema); Mariz (auth forms) |
| **Nathalie** | Design core schema (Users, Sessions, Subscriptions); first migration; ER diagram | Vrajesh (fields features need) |
| **Mathew** | Set up testing framework + CI; baseline research: customer, competitor scan | Mariz (customer-discovery plan) |
| **Together** | **Tauri setup** — Vrajesh leads config, Mariz verifies frontend loads, Nathalie confirms DB path | pair session |

**Collaboration hotspots:** Auth = Mariz + Vrajesh + Nathalie (UI ↔ API ↔ schema). Tauri = whole-team pairing.

---

## Sprint 2 — Core features working (Oct 13 – Oct 26)
*Oct 13 progress review falls in this sprint.*

| Owner | Tasks | Collaborates with |
|-------|-------|-------------------|
| **Mariz** | Logged-out feature pages (each feature explained/sold); Profile, Settings, Privacy pages; PM Report 2; present Oct 13 review | Vrajesh (profile/settings data) |
| **Vrajesh** | Code Lookups endpoint; Bill upload & parse endpoint (PDF → extract) | Nathalie (storing/caching); Mathew (parse accuracy) |
| **Nathalie** | Tables for bills, line items, code cache; retention/deletion fields | Vrajesh (upload data shape) |
| **Mathew** | Test code lookup + upload; research translation/medical-code sources; start customer interviews | Vrajesh (test cases); Mariz (findings) |

**Collaboration hotspots:** Bill upload = Vrajesh (logic) + Nathalie (storage) + Mathew (accuracy). Feature-explainer pages = Mariz + Mathew (research feeds the "why it matters" copy).

---

## Sprint 3 — MVP demo-ready for the MIDTERM (Oct 27 – Nov 9)
*Highest-stakes sprint. Nov 3 = live recorded midterm. Goal: a reliable core flow to demo.*

| Owner | Tasks | Collaborates with |
|-------|-------|-------------------|
| **Mariz** | Annotated Bill Generator UI + Translation UI (languages + jargon→plain); build the integrated demo deck; PM Report 3; lead rehearsal | Vrajesh (generator/translation APIs) |
| **Vrajesh** | Annotated bill generation logic; Translation service (Gemini: languages + jargon→plain); Subscription tier gating | Nathalie (tier data); Mariz (outputs) |
| **Nathalie** | Subscription tier schema; translation/lookup caching; reliable demo data | Vrajesh (tier checks) |
| **Mathew** | Accuracy measurement of translation + flags (the "Evaluate" evidence); midterm test-results slide; demo backup path | everyone — owns "does it actually work" |

**Collaboration hotspots:** The demo = whole team rehearses role handoffs. Translation = Vrajesh (build) + Mathew (accuracy) + Mariz (present).

**Midterm reality:** one 10-min integrated deck + live MVP demo. Every member explains their own contribution. Mathew's tests + Mariz's discovery = the "Evaluate" and "Business" evidence.

---

## Sprint 4 — Remaining features + hardening (Nov 10 – Nov 23)

| Owner | Tasks | Collaborates with |
|-------|-------|-------------------|
| **Mariz** | Templates generator UI (dispute letters); User Review system UI; Email service UI (send flow); act on midterm feedback; PM Report 4 | Vrajesh (all three APIs) |
| **Vrajesh** | Dispute templates backend; Email service; Treatment/price comparison logic; Review endpoints | Nathalie (reviews + comparison data) |
| **Nathalie** | Reviews table; treatment-comparison data model/source; performance/indexes | Mathew (data validation) |
| **Mathew** | Test all new features; QA pass; boot camp Nov 14 + Kahoot (QA waiver); usability round | Mariz (usability findings) |

**Collaboration hotspots:** Treatment comparison = Nathalie (data) + Vrajesh (logic) + Mathew (validate honesty — do not invent data). Email = Mariz (UI) + Vrajesh (send).

---

## Sprint 5 — Polish → Pre-final & Showcase (Nov 24 – Dec 5)

| Owner | Tasks | Collaborates with |
|-------|-------|-------------------|
| **Mariz** | Full UI polish; Showcase deck; rehearse; act on Dec 3 rubric | all |
| **Vrajesh** | Bug fixes; stability; performance; API docs | Mathew (defects) |
| **Nathalie** | Data-integrity check; seed clean demo data; final schema doc + ER diagram | Vrajesh |
| **Mathew** | Final accuracy report; full end-to-end QA; test evidence for pre-final rubric | all |

**Dec 1 pre-final** (Suresh scores 100-pt rubric) -> **Dec 3** act on feedback -> **Dec 5 Showcase** (public panel; >=85% = paper waiver).

---

## Wrap-up — Technical handover (Dec 6 – Dec 13)

- **All:** repo history + access, setup/deploy/run instructions, architecture + data docs, testing evidence, known issues/privacy notes.
- **Nathalie:** final data-model doc. **Vrajesh:** deployment/architecture docs. **Mathew:** test/evaluation evidence. **Mariz:** PM Report 5 + final contribution record + presentation artifacts.
- **Dec 13, 11:59 PM:** everything due. Technical handover required even if the paper is waived.

---

## Feature -> Owner quick map

| Feature | Lead | Frontend | Backend | Data | Test/Research |
|---------|------|----------|---------|------|---------------|
| Home + logged-out feature pages | Mariz | Mariz | - | - | Mathew (copy/research) |
| Login & Registration | Vrajesh + Mariz | Mariz | Vrajesh | Nathalie | Mathew |
| Profile / Settings / Privacy | Mariz | Mariz | Vrajesh | Nathalie | Mathew |
| Code Lookups | Vrajesh | Mariz | Vrajesh | Nathalie | Mathew |
| Bill upload & lookup | Vrajesh | Mariz | Vrajesh | Nathalie | Mathew (accuracy) |
| Annotated Bill Generator | Vrajesh + Mariz | Mariz | Vrajesh | Nathalie | Mathew |
| Translation (languages + jargon) | Vrajesh | Mariz | Vrajesh | Nathalie (cache) | Mathew (accuracy) |
| Subscription tiers | Vrajesh | Mariz | Vrajesh | Nathalie | Mathew |
| Treatment comparison | Nathalie + Vrajesh | Mariz | Vrajesh | Nathalie | Mathew (honesty check) |
| Dispute templates | Vrajesh | Mariz | Vrajesh | - | Mathew |
| Email service | Vrajesh | Mariz | Vrajesh | - | Mathew |
| User review system | Vrajesh | Mariz | Vrajesh | Nathalie | Mathew |

**Standing rule:** every feature is a 3-way handshake — Mariz (UI) ↔ Vrajesh (API) ↔ Nathalie (data), with Mathew testing before it is "done." Agree on the API contract first so no one is blocked.

---

## Recurring cadence (all members)

- **Weekly team meeting** (required — each miss = -1%, up to -30%). Fixed slot + a mid-week async check on Discord.
- **Mariz** records decisions/owners/due-dates in the Team Progress app after every meeting and coaching session.
- **PM Reports due:** Oct 8, Oct 22, Nov 5, Nov 19, Dec 13.

---

## Key dates (from the guidebook)

| Date | Event |
|------|-------|
| Sep 29 / 30 | Virtual orientation (one session); Sprint 1 launch |
| Oct 8 | PM Report 1 due |
| Oct 13 | Virtual progress review; Sprint 2 launch |
| Oct 22 | PM Report 2 due |
| Oct 27 | Sprint 3 begins |
| Nov 3 | Recorded live virtual midterm (50 business + 50 Capstone) |
| Nov 5 | PM Report 3 due |
| Nov 10 | Sprint 4 begins |
| Nov 14 | In-person entrepreneurship boot camp + Kahoot (QA waiver) |
| Nov 19 | PM Report 4 due |
| Nov 24 | Sprint 5 begins |
| Dec 1 | Virtual pre-final |
| Dec 3 | Pre-final scores expected |
| Dec 5 | Public Showcase (>=85% panel score = paper waiver) |
| Dec 13 | PM Report 5 + final package due, 11:59 PM |

---

## Meeting prep — Orientation (Sep 29)

**Goal today:** confirm the team can explain the idea, the roles, and the Sprint-1 plan; enter orientation availability.

**30-second pitch:**
> "Candorify helps patients read their medical bills before they pay. Upload a bill, and we translate the confusing codes into plain English, flag *potential discrepancies to review* — duplicates, math errors, charges far above Medicare rates — and generate a dispute letter. We never alter the bill or confirm errors; we surface what to question."

**Confirm today:**
- Roles (as above) — everyone agrees?
- Weekly meeting day/time (pick now).
- Enter orientation availability for BOTH options (Tue 9/29 6–8 PM or Wed 9/30 2–3:30 PM).
- Set up the Team Progress app + Discord PM channel.

**Business talking points (Prof. Kumar's lens):**
- Customer: high-deductible-plan patients who pay full price out of pocket.
- Problem: bills are vague by design; itemized bills hide duplicate/arithmetic errors.
- Value vs. auditors: we cover small-dollar cases auditors won't touch, cheaply.
- Discovery plan (no invented users): who we will interview in S1–S2, how many, by when.
- Current status (be truthful): working prototype exists (auth, code lookup, bill upload + AI extraction, translation, tiers, dispute templates) = MVP baseline; remaining features (treatment comparison, reviews, email polish) = this semester's roadmap.

**Top risks to raise:**
- Accuracy of AI translation/flagging (Mathew measures it — our "Evaluate" evidence).
- Privacy/legal (medical data, non-HIPAA disclaimer; PII stripping + deletion).
- Scope: 11 features is a lot — sequence, don't build all at once.

**Questions for orientation:**
- Confirmed orientation time/link?
- Constraints on using AI (Gemini) in the product for the evidence rules?
- Expected depth for the Nov 3 midterm demo?

---

## Where we work

- **Canvas** — official assignments & submissions
- **Discord** — team + PM communication
- **Team Progress app** (progress.real-world-connections.com) — sprint, meeting, contribution, action records
- **GitHub** — code, issues/cards, milestones
