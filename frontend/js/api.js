/* Candorify shared API client.
 * Works for both the website and the mobile app. The mobile build sets
 * window.CANDORIFY_API_BASE to the deployed backend URL; the website leaves it
 * empty so requests are same-origin.
 */
(function (global) {
  const API_BASE = global.CANDORIFY_API_BASE || "";
  const TOKEN_KEY = "candorify_token";

  function getToken() { return localStorage.getItem(TOKEN_KEY) || ""; }
  function setToken(t) { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); }
  function isLoggedIn() { return !!getToken(); }

  async function request(path, { method = "GET", body, form, auth = true } = {}) {
    const headers = {};
    const opts = { method, headers };
    if (auth && getToken()) headers["Authorization"] = "Bearer " + getToken();
    if (form) {
      opts.body = new URLSearchParams(form);
      headers["Content-Type"] = "application/x-www-form-urlencoded";
    } else if (body !== undefined) {
      opts.body = JSON.stringify(body);
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(API_BASE + path, opts);
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (!res.ok) {
      const detail = (data && data.detail) ? data.detail : ("Request failed (" + res.status + ")");
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  const API = {
    getToken, setToken, isLoggedIn,
    health: () => request("/api/health", { auth: false }),
    disclaimer: () => request("/api/disclaimer", { auth: false }),

    // Auth
    register: (email, password, preferred_language) =>
      request("/api/auth/register", { method: "POST", auth: false, body: { email, password, preferred_language } }),
    login: (email, password) =>
      request("/api/auth/login", { method: "POST", auth: false, form: { username: email, password } }),
    me: () => request("/api/auth/me"),

    // Bills
    generate: (opts) => request("/api/bills/generate", { method: "POST", body: opts }),
    submitBill: (bill) => request("/api/bills", { method: "POST", body: bill }),
    getBill: (id) => request("/api/bills/" + id),
    recheck: (id) => request("/api/bills/" + id + "/recheck", { method: "POST" }),
    updateFlag: (flagId, status) => request("/api/bills/flags/" + flagId, { method: "PATCH", body: { status } }),
    translateBill: (id, lang) => request("/api/bills/" + id + "/translate?target_language=" + encodeURIComponent(lang)),
    benchmarkBill: (id) => request("/api/bills/" + id + "/benchmark"),
    deleteBill: (id) => request("/api/bills/" + id, { method: "DELETE" }),
    score: (numBills = 100) => request("/api/bills/score?num_bills=" + numBills, { method: "POST" }),

    // Translation
    languages: () => request("/api/translate/languages", { auth: false }),
    translateCode: (code, code_system, target_language) =>
      request("/api/translate/code", { method: "POST", auth: false, body: { code, code_system, target_language } }),

    // Templates
    listTemplates: () => request("/api/templates"),
    renderTemplate: (template, context) =>
      request("/api/templates/render", { method: "POST", body: { template, context } }),

    // Payments
    paymentConfig: () => request("/api/payments/config", { auth: false }),
    startCheckout: () => request("/api/payments/checkout", { method: "POST" }),
    confirmCheckout: (sessionId) => request("/api/payments/confirm?session_id=" + encodeURIComponent(sessionId)),

    // Privacy
    privacyPolicy: () => request("/api/privacy/policy", { auth: false }),
    deleteMe: () => request("/api/privacy/me", { method: "DELETE" }),
  };

  global.CandorifyAPI = API;
})(window);
