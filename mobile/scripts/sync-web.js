/* Copies the shared web frontend into the Capacitor `www/` directory and
 * injects the mobile API base URL. Run via `npm run sync-web`.
 *
 * The mobile app is not same-origin with the backend, so it must point at the
 * deployed API. Set CANDORIFY_API_BASE in the environment (defaults to the
 * local dev server for simulator testing).
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const WEB = path.resolve(ROOT, "..", "frontend");
const WWW = path.resolve(ROOT, "www");
const API_BASE = process.env.CANDORIFY_API_BASE || "http://localhost:8000";

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function main() {
  if (!fs.existsSync(WEB)) {
    console.error("Cannot find web frontend at " + WEB);
    process.exit(1);
  }
  // Fresh copy
  fs.rmSync(WWW, { recursive: true, force: true });
  copyDir(WEB, WWW);

  // Point the mobile build at the deployed backend.
  const indexPath = path.join(WWW, "index.html");
  let html = fs.readFileSync(indexPath, "utf8");
  html = html.replace(
    /window\.CANDORIFY_API_BASE\s*=\s*"[^"]*";/,
    `window.CANDORIFY_API_BASE = ${JSON.stringify(API_BASE)};`
  );
  // Load the mobile bridge (deep links / back button) before app.js.
  html = html.replace(
    '<script src="js/app.js"></script>',
    '<script src="js/mobile.js"></script>\n  <script src="js/app.js"></script>'
  );
  fs.writeFileSync(indexPath, html);

  console.log("Synced web -> www with API base: " + API_BASE);
}

main();
