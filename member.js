(() => {
  const state = { config: null, session: null, recovery: false, checkoutEmail: "" };
  const $ = (id) => document.getElementById(id);
  const show = (id, visible = true) => { $(id).hidden = !visible; };
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const date = (value) => value ? new Date(value).toLocaleString() : "—";
  const money = (value) => value == null ? "—" : Number(value).toLocaleString(undefined, { style: "currency", currency: "USD" });

  function saveSession(session) {
    state.session = session;
    if (session) localStorage.setItem("eti_member_session", JSON.stringify(session));
    else localStorage.removeItem("eti_member_session");
  }

  function showMemberNavigation(visible) {
    show("nav-signout-button", visible);
    show("member-login-link", !visible);
    $("member-home-link").href = visible ? "members.html" : "index.html";
    $("member-home-link").textContent = "Home";
  }

  function readCallback() {
    const hash = new URLSearchParams(location.hash.slice(1));
    if (!hash.get("access_token")) return;
    state.recovery = hash.get("type") === "recovery";
    saveSession({ access_token: hash.get("access_token"), refresh_token: hash.get("refresh_token"), expires_at: Math.floor(Date.now() / 1000) + Number(hash.get("expires_in") || 3600) });
    history.replaceState(null, "", location.pathname + location.search);
  }

  async function refreshSession() {
    if (!state.session?.refresh_token) return false;
    const response = await fetch(`${state.config.supabaseUrl}/auth/v1/token?grant_type=refresh_token`, { method: "POST", headers: { apikey: state.config.supabaseAnonKey, "content-type": "application/json" }, body: JSON.stringify({ refresh_token: state.session.refresh_token }) });
    if (!response.ok) { saveSession(null); return false; }
    const payload = await response.json();
    saveSession({ access_token: payload.access_token, refresh_token: payload.refresh_token, expires_at: Math.floor(Date.now() / 1000) + payload.expires_in });
    return true;
  }

  async function api(path, options = {}) {
    if (state.session?.expires_at < Math.floor(Date.now() / 1000) + 30) await refreshSession();
    return fetch(path, { ...options, headers: { "content-type": "application/json", authorization: `Bearer ${state.session?.access_token || ""}`, ...(options.headers || {}) } });
  }

  async function authRequest(path, body, method = "POST") {
    const options = { method, headers: { apikey: state.config.supabaseAnonKey, authorization: `Bearer ${state.session?.access_token || ""}`, "content-type": "application/json" } };
    if (method !== "GET" && method !== "HEAD") options.body = JSON.stringify(body);
    return fetch(`${state.config.supabaseUrl}/auth/v1/${path}`, options);
  }

  function adoptAuth(payload) {
    if (!payload.access_token) return false;
    saveSession({ access_token: payload.access_token, refresh_token: payload.refresh_token, expires_at: Math.floor(Date.now() / 1000) + payload.expires_in });
    return true;
  }

  function table(columns, rows) {
    if (!rows.length) return '<p class="empty">Nothing to show right now.</p>';
    return `<table><thead><tr>${columns.map((c) => `<th>${escapeHtml(c.label)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map((c) => `<td>${c.render ? c.render(row[c.key], row) : escapeHtml(row[c.key])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }

  function render(data) {
    $("position-count").textContent = data.positions.length; $("alert-count").textContent = data.alerts.length; $("trade-count").textContent = data.trades.length;
    $("updated-at").textContent = `Updated ${date(data.updatedAt)}`;
    $("alerts-table").innerHTML = table([{key:"time",label:"Time",render:date},{key:"symbol",label:"Symbol"},{key:"action",label:"Action"},{key:"quantity",label:"Quantity"},{key:"status",label:"Status"}], data.alerts);
    $("positions-table").innerHTML = table([{key:"openedAt",label:"Opened",render:date},{key:"symbol",label:"Symbol"},{key:"quantity",label:"Quantity"},{key:"averagePrice",label:"Average price",render:money}], data.positions);
    $("trades-table").innerHTML = table([{key:"closedAt",label:"Closed",render:date},{key:"symbol",label:"Symbol"},{key:"side",label:"Side",render:(v)=>String(v)==="1"?"Long":String(v)==="2"?"Short":escapeHtml(v)},{key:"quantity",label:"Quantity"},{key:"openPrice",label:"Open",render:money},{key:"closePrice",label:"Close",render:money},{key:"profitLoss",label:"P/L",render:(v)=>`<span class="${Number(v)>=0?"positive":"negative"}">${money(v)}</span>`}], data.trades);
  }

  async function renderMemberView(data) {
    const today = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
    $("current-date").textContent = today;
    $("detail-current-date").textContent = `Current date: ${today}`;
    const strategy = new URLSearchParams(location.search).get("strategy") || "";
    const showDetail = Boolean(strategy);
    show("strategy-directory", !showDetail);
    show("strategy-detail", showDetail);
    if (strategy === "extreme-os") render(data);
    if (showDetail && strategy !== "extreme-os") {
      const response = await api(`/api/member-page?strategy=${encodeURIComponent(strategy)}`);
      if (!response.ok) throw new Error("Member strategy page is unavailable.");
      const html = await response.text();
      document.open();
      document.write(html);
      document.close();
    }
  }

  async function loadStrategiesHome() {
    show("loading"); show("auth-panel", false); show("activate-panel", false); show("password-panel", false); show("strategies-home", false); show("account-actions", false);
    if (!state.session) { show("loading", false); show("auth-panel"); return; }
    if (state.recovery) { show("loading", false); show("password-panel"); return; }
    const userResponse = await authRequest("user", {}, "GET");
    if (!userResponse.ok) { saveSession(null); show("loading", false); show("auth-panel"); return; }
    const user = await userResponse.json(); $("member-email").textContent = user.email;
    const strategy = new URLSearchParams(location.search).get("strategy") || "";

    // The directory only needs an access check. Live Collective2 data is fetched
    // only when the member actually opens Extreme OS; other protected pages
    // perform their access check in /api/member-page.
    if (strategy && strategy !== "extreme-os") {
      showMemberNavigation(true);
      await renderMemberView(null);
      show("loading", false); show("account-actions"); show("strategies-home");
      return;
    }

    const response = await api(strategy === "extreme-os" ? "/api/member-data" : "/api/member-access");
    show("loading", false); show("account-actions");
    if (response.status === 401) { saveSession(null); show("account-actions", false); show("auth-panel"); return; }
    if (response.status === 403) {
      saveSession(null); show("account-actions", false); show("auth-panel");
      $("auth-message").textContent = "This email does not have an active subscription. Subscribe before signing in.";
      return;
    }
    if (!response.ok) { show("auth-panel"); $("auth-message").textContent = "Member data is temporarily unavailable."; return; }
    showMemberNavigation(true);
    const data = await response.json(); await renderMemberView(strategy === "extreme-os" ? data : null); show("strategies-home");
  }

  $("login-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const button = event.submitter; button.disabled = true;
    const response = await authRequest("token?grant_type=password", { email: $("email").value, password: $("password").value });
    const payload = await response.json();
    if (response.ok && adoptAuth(payload)) { $("auth-message").textContent = ""; await loadStrategiesHome(); }
    else $("auth-message").textContent = payload.error_description || payload.msg || "Incorrect email or password.";
    button.disabled = false;
  });

  $("activate-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.checkoutEmail || !$("activate-password").reportValidity()) return;
    const button = event.submitter; button.disabled = true;
    const confirmationUrl = `${location.origin}/members.html`;
    const response = await authRequest(`signup?redirect_to=${encodeURIComponent(confirmationUrl)}`, { email: state.checkoutEmail, password: $("activate-password").value }); const payload = await response.json();
    if (response.ok && adoptAuth(payload)) await loadStrategiesHome();
    else if (response.ok) $("activate-message").textContent = "Check your email to confirm your account, then sign in.";
    else $("activate-message").textContent = payload.msg || payload.error_description || "Unable to create account.";
    button.disabled = false;
  });

  $("reset-button").addEventListener("click", async () => {
    if (!$("email").reportValidity()) return;
    const response = await authRequest("recover", { email: $("email").value, redirect_to: `${location.origin}/members.html` });
    $("auth-message").textContent = response.ok ? "Check your email for the password-reset link." : "Unable to send the reset email.";
  });

  $("password-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const response = await authRequest("user", { password: $("new-password").value }, "PUT");
    if (response.ok) { state.recovery = false; $("password-message").textContent = "Password updated."; await loadStrategiesHome(); }
    else $("password-message").textContent = "Unable to update the password.";
  });

  $("billing-button").addEventListener("click", async () => { const response = await api("/api/create-portal-session", { method: "POST", body: "{}" }); const body = await response.json(); if (body.url) location.href = body.url; else alert(body.error || "Unable to open billing."); });
  $("nav-signout-button").addEventListener("click", () => { saveSession(null); location.href = "members.html"; });

  (async () => {
    state.config = await fetch("/api/public-config").then((r) => r.json()); readCallback();
    if (!state.session) { try { saveSession(JSON.parse(localStorage.getItem("eti_member_session"))); } catch {} }
    if (!state.config.supabaseUrl || !state.config.supabaseAnonKey) { show("loading", false); show("auth-panel"); $("auth-message").textContent = "Member accounts are being configured."; return; }
    const query = new URLSearchParams(location.search);
    const checkoutSessionId = query.get("checkout") === "success" ? query.get("session_id") : "";
    if (checkoutSessionId && !state.session) {
      const checkout = await fetch(`/api/checkout-status?session_id=${encodeURIComponent(checkoutSessionId)}`);
      if (checkout.ok) {
        const result = await checkout.json(); state.checkoutEmail = result.email;
        $("checkout-email").textContent = result.email; show("loading", false); show("auth-panel", false); show("activate-panel"); return;
      }
      $("auth-message").textContent = "We could not verify that subscription. Please contact support if you completed payment.";
    }
    await loadStrategiesHome();
  })().catch(() => { show("loading", false); show("auth-panel"); $("auth-message").textContent = "Member sign-in is temporarily unavailable."; });
})();
