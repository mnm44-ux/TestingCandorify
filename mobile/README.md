# Candorify Mobile (iOS + Android)

The mobile app is a **Capacitor** wrapper around the same web frontend in
`../frontend`, so there is a single UI codebase across web, iOS, and Android.
The shared API client (`js/api.js`) talks to the same FastAPI backend; on
mobile the API base URL is injected at build time (it can't be same-origin).

## Why Capacitor

- One codebase (HTML/CSS/JS) → real native iOS and Android apps.
- Native shell provides hardware back button, deep links (for Stripe return),
  push, and app-store packaging.
- No framework lock-in; the web app already works standalone.

## Prerequisites

- Node.js 18+
- Android: Android Studio + SDK
- iOS: macOS + Xcode

## Build & run

```bash
cd mobile
npm install

# Point the app at your deployed (or local) backend:
export CANDORIFY_API_BASE="https://your-candorify-api.example.com"
# For a local backend + Android emulator use: http://10.0.2.2:8000
# For a local backend + iOS simulator use:    http://localhost:8000

npm run build          # copies frontend -> www and injects API base

# First-time platform setup:
npm run add:android    # or: npm run add:ios

# Sync and open in the native IDE:
npm run open:android   # or: npm run open:ios

# Or run directly on a connected device / emulator:
npm run run:android    # or: npm run run:ios
```

## How it works

1. `scripts/sync-web.js` copies `../frontend` into `www/`, rewrites
   `window.CANDORIFY_API_BASE`, and injects `js/mobile.js` (native bridge).
2. `npx cap sync` copies `www/` into the native projects.
3. The native app loads the web UI; `mobile.js` wires the Android back button
   and the Stripe deep-link return.

## Payments on mobile

Stripe Checkout opens in the in-app browser; on completion the app returns via
a deep link (`candorify://payment-return?session_id=...`) which `mobile.js`
confirms with the backend. In test/mock mode the upgrade completes locally.
