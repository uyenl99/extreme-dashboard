(() => {
  const SESSION_KEY = "eti_member_session";
  const MEMBER_DIRECTORY_URL = "/members.html?view=strategies&nav=13";
  const root = document.documentElement;

  root.classList.add("auth-nav-pending");
  const pendingStyle = document.createElement("style");
  pendingStyle.textContent = `
    .auth-nav-pending nav.site-nav,
    .auth-nav-pending body > nav:first-of-type { visibility: hidden; }
    .global-auth-nav-button {
      margin-left: 20px;
      padding: 0;
      border: 0;
      background: none;
      color: white;
      font: inherit;
      cursor: pointer;
    }
  `;
  document.head.appendChild(pendingStyle);

  function readSession() {
    try {
      const session = JSON.parse(localStorage.getItem(SESSION_KEY));
      return session && typeof session.access_token === "string" && session.access_token
        ? session
        : null;
    } catch {
      return null;
    }
  }

  function saveSession(session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }

  function findLink(nav, label) {
    return [...nav.querySelectorAll("a")].find(
      (link) => link.textContent.trim().toLowerCase() === label.toLowerCase()
    );
  }

  async function freshAccessToken() {
    let session = readSession();
    if (!session) return "";
    if (!session.expires_at || session.expires_at >= Math.floor(Date.now() / 1000) + 30) {
      return session.access_token;
    }
    if (!session.refresh_token) return session.access_token;

    const config = await fetch("/api/public-config").then((response) => response.json());
    const response = await fetch(
      `${config.supabaseUrl}/auth/v1/token?grant_type=refresh_token`,
      {
        method: "POST",
        headers: {
          apikey: config.supabaseAnonKey,
          "content-type": "application/json"
        },
        body: JSON.stringify({ refresh_token: session.refresh_token })
      }
    );
    if (!response.ok) return "";

    const payload = await response.json();
    session = {
      access_token: payload.access_token,
      refresh_token: payload.refresh_token,
      expires_at: Math.floor(Date.now() / 1000) + payload.expires_in
    };
    saveSession(session);
    return session.access_token;
  }

  async function openBilling(button) {
    button.disabled = true;
    try {
      const accessToken = await freshAccessToken();
      if (!accessToken) {
        localStorage.removeItem(SESSION_KEY);
        location.href = "/members.html";
        return;
      }
      const response = await fetch("/api/create-portal-session", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${accessToken}`
        },
        body: "{}"
      });
      const payload = await response.json();
      if (payload.url) location.href = payload.url;
      else alert(payload.error || "Unable to open billing.");
    } catch {
      alert("Unable to open billing.");
    } finally {
      button.disabled = false;
    }
  }

  function renderAuthenticatedNavigation(nav) {
    const homeLink = findLink(nav, "Home");
    const strategiesLink = findLink(nav, "Strategies");
    if (homeLink) homeLink.href = "/index.html";
    if (strategiesLink) strategiesLink.href = MEMBER_DIRECTORY_URL;

    findLink(nav, "Login")?.remove();

    const links = nav.querySelector(".navlinks") || nav.lastElementChild || nav;
    const hasBilling = nav.querySelector(
      "#global-billing-button, #billing-button, #detail-billing-button"
    );
    if (!hasBilling) {
      const billing = document.createElement("button");
      billing.id = "global-billing-button";
      billing.className = "global-auth-nav-button";
      billing.type = "button";
      billing.textContent = "Manage billing";
      billing.addEventListener("click", () => openBilling(billing));
      links.appendChild(billing);
    }

    const hasSignOut = nav.querySelector(
      "#global-signout-button, #nav-signout-button, #detail-signout-button"
    );
    if (!hasSignOut) {
      const signOut = document.createElement("button");
      signOut.id = "global-signout-button";
      signOut.className = "global-auth-nav-button";
      signOut.type = "button";
      signOut.textContent = "Sign out";
      signOut.addEventListener("click", () => {
        localStorage.removeItem(SESSION_KEY);
        location.href = "/members.html";
      });
      links.appendChild(signOut);
    }
  }

  let navigationObserver;
  let navigationApplied = false;

  function applyNavigationWhenReady() {
    if (navigationApplied) return true;
    const nav = document.querySelector("nav.site-nav, body > nav:first-of-type");
    if (!nav) return false;

    // Wait until the parser has completed the menu. Otherwise the observer can
    // run after <nav> opens but before the Login/About/Contact links exist.
    if (!["Home", "Strategies", "About", "Contact"].every((label) => findLink(nav, label))) {
      return false;
    }

    try {
      if (readSession()) renderAuthenticatedNavigation(nav);
    } finally {
      navigationApplied = true;
      root.classList.remove("auth-nav-pending");
      navigationObserver?.disconnect();
    }
    return true;
  }

  // This observer runs as soon as the parser creates the complete navigation,
  // before large charts and tables finish parsing and before the first paint.
  navigationObserver = new MutationObserver(() => applyNavigationWhenReady());
  navigationObserver.observe(root, { childList: true, subtree: true });
  applyNavigationWhenReady();

  // Fallback for malformed or future pages without the standard menu.
  document.addEventListener("DOMContentLoaded", () => {
    if (!applyNavigationWhenReady()) {
      navigationObserver.disconnect();
      root.classList.remove("auth-nav-pending");
    }
  }, { once: true });
})();
