/* Candorify SPA controller (vanilla JS). Shared by web + mobile. */
(function () {
  const API = window.CandorifyAPI;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  let state = {
    user: null,          // { email, tier } or null
    currentBill: null,   // last generated/loaded bill
    languages: { en: "English" },
  };

  // ---------- utilities ----------
  function money(n) { return "$" + Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

  let toastTimer;
  function toast(msg, isErr = false) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.toggle("err", isErr);
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
  }

  function isPaid() { return state.user && state.user.tier === "paid"; }

  // ---------- navigation ----------
  function showView(id) {
    $$(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + id));
    $$("nav.top button[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === id));
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (id === "pricing") renderPricing();
    if (id === "account") renderAccount();
  }

  // ---------- auth UI ----------
  async function refreshUser() {
    if (!API.isLoggedIn()) { state.user = null; renderAuthBar(); return; }
    try { state.user = await API.me(); }
    catch { API.setToken(""); state.user = null; }
    renderAuthBar();
  }

  function renderAuthBar() {
    const authArea = $("#auth-area");
    if (state.user) {
      const pill = `<span class="pill ${state.user.tier}">${state.user.tier.toUpperCase()}</span>`;
      authArea.innerHTML = `${pill} <button class="linkbtn" data-view="account">${esc(state.user.email)}</button>
        <button class="btn ghost sm" id="btn-logout">Log out</button>`;
      $("#btn-logout").onclick = () => { API.setToken(""); state.user = null; renderAuthBar(); toast("Logged out"); showView("home"); };
      $('[data-view="account"]', authArea).onclick = () => showView("account");
    } else {
      authArea.innerHTML = `<button class="btn ghost sm" id="btn-show-login">Log in</button>
        <button class="btn primary sm" id="btn-show-register">Sign up</button>`;
      $("#btn-show-login").onclick = () => { showView("auth"); $("#auth-mode-login").checked = true; };
      $("#btn-show-register").onclick = () => { showView("auth"); $("#auth-mode-register").checked = true; };
    }
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    const email = $("#auth-email").value.trim();
    const password = $("#auth-password").value;
    const lang = $("#auth-lang").value;
    const isRegister = $("#auth-mode-register").checked;
    try {
      const res = isRegister ? await API.register(email, password, lang) : await API.login(email, password);
      API.setToken(res.access_token);
      await refreshUser();
      toast(isRegister ? "Account created" : "Welcome back");
      showView("review");
    } catch (err) { toast(err.message, true); }
  }

  // ---------- bill generation + review ----------
  async function generateBill() {
    const num = parseInt($("#gen-lines").value, 10) || 8;
    const inject = $("#gen-inject").checked;
    const btn = $("#btn-generate");
    btn.disabled = true; btn.textContent = "Generating…";
    try {
      const bill = await API.generate({ num_line_items: num, inject_errors: inject, error_rate: 0.35 });
      state.currentBill = bill;
      renderBill(bill);
      showView("review");
      toast("Synthetic bill generated");
    } catch (err) { toast(err.message, true); }
    finally { btn.disabled = false; btn.textContent = "Generate synthetic bill"; }
  }

  function flagLineSet(bill) {
    const set = new Set();
    bill.flags.forEach(f => (f.line_item_ids || "").split(",").filter(Boolean).forEach(id => set.add(parseInt(id, 10))));
    return set;
  }

  function renderBill(bill) {
    const wrap = $("#bill-detail");
    if (!bill) { wrap.innerHTML = `<p class="muted">No bill yet. Generate one to get started.</p>`; return; }
    const flaggedIds = flagLineSet(bill);
    const subtotal = bill.line_items.reduce((s, li) => s + (li.line_total || 0), 0);

    const rows = bill.line_items.map(li => `
      <tr class="${flaggedIds.has(li.id) ? "flagged" : ""}">
        <td>${li.position + 1}</td>
        <td><strong>${esc(li.code)}</strong> <span class="muted">${esc(li.code_system)}</span></td>
        <td>${esc(li.description)}</td>
        <td class="num">${li.quantity}</td>
        <td class="num">${money(li.unit_price)}</td>
        <td class="num">${money(li.line_total)}</td>
      </tr>`).join("");

    const flags = bill.flags.length
      ? bill.flags.map(f => renderFlag(f)).join("")
      : `<p class="muted">No potential discrepancies were surfaced. That doesn't guarantee the bill is correct — review each line yourself.</p>`;

    wrap.innerHTML = `
      <div class="card">
        <div class="row">
          <h2 style="margin:0">${esc(bill.provider_name)}</h2>
          <span class="pill free">SYNTHETIC</span>
          <div class="spacer"></div>
          <button class="btn ghost sm" id="btn-delete-bill">🗑 Delete bill</button>
        </div>
        <p class="muted">Patient: ${esc(bill.patient_name)} · Service date: ${esc(bill.service_date)}
          ${bill.provider_npi ? "· NPI: " + esc(bill.provider_npi) : ""}</p>
        <table>
          <thead><tr><th>#</th><th>Code</th><th>Description</th><th class="num">Qty</th><th class="num">Unit</th><th class="num">Line total</th></tr></thead>
          <tbody>${rows}</tbody>
          <tfoot>
            <tr><td colspan="5" class="num"><strong>Sum of lines</strong></td><td class="num"><strong>${money(subtotal)}</strong></td></tr>
            <tr><td colspan="5" class="num">Stated total on bill</td><td class="num">${money(bill.stated_total)}</td></tr>
          </tfoot>
        </table>
      </div>

      <div class="card" style="margin-top:18px">
        <div class="row">
          <h2 style="margin:0">Potential discrepancies to review</h2>
          <div class="spacer"></div>
          <select id="translate-lang" class="hidden" style="width:auto"></select>
          <button class="btn ghost sm" id="btn-translate">🌐 Translate each line</button>
          <button class="btn ghost sm" id="btn-benchmark">📊 Compare to Medicare</button>
        </div>
        <p class="notice">These are <strong>possible</strong> issues for you to confirm or dismiss. Candorify never confirms an error.</p>
        <div id="flags-list">${flags}</div>
        <div id="translations"></div>
        <div id="benchmarks"></div>
      </div>`;

    $("#btn-delete-bill").onclick = () => deleteCurrentBill(bill.id);
    $("#btn-translate").onclick = () => translateLines(bill.id);
    $("#btn-benchmark").onclick = () => benchmarkLines(bill.id);
    wireFlagButtons(bill);
    populateLangSelect($("#translate-lang"));
  }

  function renderFlag(f) {
    const cls = f.status === "confirmed" ? "confirmed" : f.status === "dismissed" ? "dismissed" : "";
    const tag = f.status !== "open" ? `<span class="status-tag">${f.status}</span>` : "";
    return `
      <div class="flag ${cls}" data-flag-id="${f.id}">
        <div class="row"><span class="kind">${esc(f.kind.replace("_", " "))}</span> ${tag}</div>
        <div class="msg">${esc(f.message)}</div>
        <div class="row">
          <button class="btn ghost sm" data-action="confirmed">Confirm for follow-up</button>
          <button class="btn ghost sm" data-action="dismissed">Dismiss</button>
          <button class="btn ghost sm" data-action="open">Reset</button>
        </div>
      </div>`;
  }

  function wireFlagButtons(bill) {
    $$("#flags-list .flag").forEach(el => {
      const flagId = parseInt(el.dataset.flagId, 10);
      $$("button[data-action]", el).forEach(btn => {
        btn.onclick = async () => {
          try {
            await API.updateFlag(flagId, btn.dataset.action);
            const f = bill.flags.find(x => x.id === flagId);
            if (f) f.status = btn.dataset.action;
            el.outerHTML = renderFlag(f);
            wireFlagButtons(bill);
            toast("Flag marked '" + btn.dataset.action + "'");
          } catch (err) { toast(err.message, true); }
        };
      });
    });
  }

  async function deleteCurrentBill(id) {
    if (!confirm("Delete this bill and all its data now? This cannot be undone.")) return;
    try { await API.deleteBill(id); state.currentBill = null; renderBill(null); toast("Bill deleted"); }
    catch (err) { toast(err.message, true); }
  }

  // ---------- translation ----------
  function populateLangSelect(sel) {
    if (!sel) return;
    sel.innerHTML = Object.entries(state.languages).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
    if (state.user && state.user.preferred_language) sel.value = state.user.preferred_language;
  }

  async function translateLines(billId) {
    if (!isPaid()) { toast("Line-by-line translation is a paid feature.", true); showView("pricing"); return; }
    const sel = $("#translate-lang");
    sel.classList.remove("hidden");
    const lang = sel.value || "en";
    const out = $("#translations");
    out.innerHTML = `<p class="loading">Translating…</p>`;
    try {
      const res = await API.translateBill(billId, lang);
      out.innerHTML = `<h3>Plain-English translation (${esc(state.languages[lang] || lang)})</h3>` +
        res.lines.map(l => `<div class="flag" style="border-left-color:var(--brand-2)">
          <div class="kind">Line ${l.position + 1} · ${esc(l.code)}</div>
          <div class="msg"><strong>English:</strong> ${esc(l.plain_english)}<br>
          ${lang !== "en" ? `<strong>${esc(state.languages[lang])}:</strong> ${esc(l.translated)}` : ""}</div>
        </div>`).join("");
    } catch (err) {
      out.innerHTML = "";
      if (err.status === 402) { toast("Paid feature — upgrade to unlock translation.", true); showView("pricing"); }
      else toast(err.message, true);
    }
  }

  async function benchmarkLines(billId) {
    if (!isPaid()) { toast("Medicare comparison is a paid feature.", true); showView("pricing"); return; }
    const out = $("#benchmarks");
    out.innerHTML = `<p class="loading">Comparing to Medicare reference rates…</p>`;
    try {
      const res = await API.benchmarkBill(billId);
      const rows = res.lines.map(l => {
        const rate = l.medicare_rate == null ? "—" : money(l.medicare_rate);
        const ratio = l.ratio == null ? "—" : (l.ratio + "×");
        const high = l.ratio != null && l.ratio >= 5;
        return `<tr class="${high ? "flagged" : ""}">
          <td>${l.position + 1}</td><td><strong>${esc(l.code)}</strong></td>
          <td>${esc(l.description)}</td>
          <td class="num">${money(l.charged_unit_price)}</td>
          <td class="num">${rate}</td>
          <td class="num">${ratio}</td></tr>`;
      }).join("");
      out.innerHTML = `<h3>Medicare price comparison</h3>
        <p class="notice">${esc(res.disclaimer)}</p>
        <table><thead><tr><th>#</th><th>Code</th><th>Description</th>
          <th class="num">Charged</th><th class="num">Medicare ref</th><th class="num">Ratio</th></tr></thead>
          <tbody>${rows}</tbody></table>`;
    } catch (err) {
      out.innerHTML = "";
      if (err.status === 402) { toast("Paid feature — upgrade to unlock Medicare comparison.", true); showView("pricing"); }
      else toast(err.message, true);
    }
  }

  async function translateSingleCode(e) {
    e.preventDefault();
    const code = $("#tc-code").value.trim();
    const system = $("#tc-system").value;
    const lang = $("#tc-lang").value;
    const out = $("#tc-result");
    out.innerHTML = `<p class="loading">Looking up…</p>`;
    try {
      const r = await API.translateCode(code, system, lang);
      out.innerHTML = `<div class="card" style="margin-top:14px">
        <div class="muted">${esc(r.code)} · ${esc(r.code_system)} · source: ${esc(r.source)}</div>
        <p><strong>Plain English:</strong> ${esc(r.plain_english)}</p>
        ${lang !== "en" ? `<p><strong>${esc(state.languages[lang] || lang)}:</strong> ${esc(r.translated)}</p>` : ""}
      </div>`;
    } catch (err) { out.innerHTML = ""; toast(err.message, true); }
  }

  // ---------- templates ----------
  async function renderTemplateFor(kind) {
    const ctx = {
      provider_name: $("#tpl-provider").value || "Your Provider",
      patient_name: $("#tpl-patient").value || "Your Name",
      account_number: $("#tpl-account").value || "",
      service_date: $("#tpl-date").value || "",
      patient_contact: $("#tpl-contact").value || "",
    };
    if (kind === "dispute_charge") {
      ctx.items = [{ code: $("#tpl-item-code").value, description: $("#tpl-item-desc").value, note: $("#tpl-item-note").value || "please confirm this charge" }];
    }
    try {
      const r = await API.renderTemplate(kind, ctx);
      $("#tpl-subject").value = r.subject;
      $("#tpl-body").value = r.body;
      toast("Template ready — edit freely before sending");
    } catch (err) {
      if (err.status === 402) { toast("Dispute letters are a paid feature.", true); showView("pricing"); }
      else toast(err.message, true);
    }
  }

  // ---------- pricing / payments ----------
  async function renderPricing() {
    let cfg = { paid_features: [], mock_mode: true };
    try { cfg = await API.paymentConfig(); } catch {}
    $("#paid-features").innerHTML = cfg.paid_features.map(f => `<li>${esc(f)}</li>`).join("");
    $("#pay-mode-note").textContent = cfg.mock_mode
      ? "Test mode: no real charge is made. Use this to demo the upgrade flow."
      : "Secure checkout powered by Stripe.";
    $("#btn-upgrade").onclick = startUpgrade;
  }

  async function startUpgrade() {
    if (!API.isLoggedIn()) { toast("Please log in or sign up first.", true); showView("auth"); return; }
    try {
      const res = await API.startCheckout();
      // Mock mode returns a URL back to our confirm endpoint; real Stripe returns hosted URL.
      if (res.mock) {
        // Complete the mock flow directly (no external redirect available offline).
        const sid = new URL(res.checkout_url, window.location.origin).searchParams.get("session_id");
        await API.confirmCheckout(sid);
        await refreshUser();
        toast("Upgraded to paid (test mode)! Paid features unlocked.");
        showView("account");
      } else {
        window.location.href = res.checkout_url;
      }
    } catch (err) { toast(err.message, true); }
  }

  // ---------- account / privacy ----------
  async function renderAccount() {
    const wrap = $("#account-detail");
    if (!state.user) { wrap.innerHTML = `<p class="muted">Log in to view your account.</p>`; return; }
    let policy = { retention_days: 30, summary: "" };
    try { policy = await API.privacyPolicy(); } catch {}
    wrap.innerHTML = `
      <p><strong>Email:</strong> ${esc(state.user.email)}</p>
      <p><strong>Plan:</strong> <span class="pill ${state.user.tier}">${state.user.tier.toUpperCase()}</span></p>
      ${state.user.tier === "free" ? `<button class="btn primary" id="acc-upgrade">Upgrade to paid</button>` : ""}
      <hr style="border-color:var(--border);margin:20px 0">
      <h3>Your privacy</h3>
      <p class="muted">${esc(policy.summary)}</p>
      <p class="muted">Uploads auto-delete after <strong>${policy.retention_days} days</strong>.</p>
      <button class="btn danger" id="acc-delete">One-tap: delete my account & all data</button>`;
    if ($("#acc-upgrade")) $("#acc-upgrade").onclick = () => showView("pricing");
    $("#acc-delete").onclick = async () => {
      if (!confirm("Permanently delete your account and ALL associated data now?")) return;
      try { await API.deleteMe(); API.setToken(""); state.user = null; renderAuthBar(); toast("Account and data deleted"); showView("home"); }
      catch (err) { toast(err.message, true); }
    };
  }

  // ---------- accuracy demo ----------
  async function runAccuracy() {
    const out = $("#accuracy-result");
    out.innerHTML = `<p class="loading">Scoring against labeled synthetic set…</p>`;
    try {
      const r = await API.score(100);
      out.innerHTML = `<div class="grid cols-3" style="margin-top:14px">
        <div class="card center"><div class="price">${(r.recall * 100).toFixed(1)}%<small> recall</small></div></div>
        <div class="card center"><div class="price">${(r.precision * 100).toFixed(1)}%<small> precision</small></div></div>
        <div class="card center"><div class="price">${(r.false_positive_rate * 100).toFixed(1)}%<small> false-positive rate</small></div></div>
      </div>
      <p class="muted" style="margin-top:12px">Evaluated ${r.bills_evaluated} labeled synthetic bills · TP ${r.true_positives} · FP ${r.false_positives} · FN ${r.false_negatives}.
      Target (recall ≥ 95%, FPR &lt; 5%): <strong style="color:${r.meets_target ? "var(--ok)" : "var(--danger)"}">${r.meets_target ? "MET" : "NOT MET"}</strong></p>`;
    } catch (err) { out.innerHTML = ""; toast(err.message, true); }
  }

  // ---------- disclaimer ----------
  async function loadDisclaimer() {
    try { const d = await API.disclaimer(); $$(".disclaimer-text").forEach(el => el.textContent = d.text); } catch {}
  }
  async function loadLanguages() {
    try { state.languages = await API.languages(); } catch {}
    populateLangSelect($("#tc-lang"));
    populateLangSelect($("#auth-lang"));
  }

  // ---------- init ----------
  function wireNav() {
    $$("nav.top button[data-view], [data-goto]").forEach(b => {
      const target = b.dataset.view || b.dataset.goto;
      if (target) b.addEventListener("click", () => showView(target));
    });
  }

  function init() {
    wireNav();
    $("#auth-form").addEventListener("submit", handleAuthSubmit);
    $("#btn-generate").addEventListener("click", generateBill);
    $("#tc-form").addEventListener("submit", translateSingleCode);
    $("#btn-tpl-request").addEventListener("click", () => renderTemplateFor("request_itemized_bill"));
    $("#btn-tpl-dispute").addEventListener("click", () => renderTemplateFor("dispute_charge"));
    $("#btn-run-accuracy").addEventListener("click", runAccuracy);

    loadDisclaimer();
    loadLanguages();
    refreshUser();

    // Handle Stripe real-mode redirect back with ?session_id=
    const params = new URLSearchParams(window.location.search);
    if (params.get("session_id")) {
      API.confirmCheckout(params.get("session_id")).then(refreshUser).then(() => {
        toast("Payment confirmed — paid features unlocked!"); showView("account");
      }).catch(() => {});
    }
    showView("home");
  }

  document.addEventListener("DOMContentLoaded", init);
})();
