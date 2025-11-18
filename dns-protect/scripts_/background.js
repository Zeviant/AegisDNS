const BACKEND_URL = "http://127.0.0.1:5005";
let backendReachable = false;
let healthTimer = null;

// Pings backend server to check status
async function pingBackend() {
  try {
    const res = await fetch(`${BACKEND_URL}/health`, { cache: "no-store" });
    backendReachable = res.ok;
    const data = backendReachable ? await res.json() : null;
    await chrome.storage.session.set({ backendReachable, health: data });
  } catch (e) {
    console.warn("Application backend unreachable (server not running or app not open):", e);
    backendReachable = false;
    await chrome.storage.session.set({ backendReachable, health: null });
  }
  scheduleHealthPolling();
  return backendReachable;
}

// Ping on browser startup
chrome.runtime.onStartup.addListener(() => {
  pingBackend();
});

// Refreshes backend reachability status
async function ensureBackend() {
  if (backendReachable) {
    return true;
  }
  return await pingBackend();
}

// Polls server every 30 seconds if reachable, every 3 seconds if unreachable
function scheduleHealthPolling() {
  if (healthTimer) {
    clearInterval(healthTimer);
    healthTimer = null;
  }
  const intervalMs = backendReachable ? 30000 : 3000;
  healthTimer = setInterval(() => {
    pingBackend();
  }, intervalMs);
}

// Logs navigations to server
async function logNavigation(details) {
  if (!isTopFrame(details)) return;
  if (!isAllowedTransition(details)) return;
  if (isSearchUrl(details.url)) return;
  if (isNoiseUrl(details.url)) return;
  const ready = await ensureBackend();
  if (!ready) return;

  const payload = {
    url: details.url,
    timestamp: Date.now(),
    mode: "logging",
  };

  try {
    await fetch(`${BACKEND_URL}/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("Failed to log navigation:", err);
  }
}

// Calls logNavigation when URL is loaded
chrome.webNavigation.onCompleted.addListener(logNavigation, {
  url: [{ schemes: ["http", "https"] }],
});

// Runs on service worker startup to start polling cycle
pingBackend();

// Filters search URLs (otherwise any search done will be logged as a navigation)
function isSearchUrl(raw) {
  try {
    const u = new URL(raw);
    const host = u.hostname;
    const path = u.pathname;
    const hasQuery = !!u.searchParams.get("q");
    if (hasQuery) {
      if (host.endsWith("google.com") && path === "/search") return true;
      if (host.endsWith("bing.com") && path === "/search") return true;
      if (host.endsWith("duckduckgo.com")) return true;
      if (host.endsWith("yahoo.com") && path === "/search") return true;
    }
  } catch (_) {}
  return false;
}

// Filters out frames which aren't the main frame (e.g. ads, login windows, embedded content)
function isTopFrame(details) {
  return details.frameId === 0;
}

// Only keeps user-initiated navigations (e.g. clicks, typing, back/forward)
// Reloading and auto_bookmark will mostly be redundant, could maybe be filtered in more
// expensive modes (@nicovporta)
function isAllowedTransition(details) {
  if (!details || typeof details.transitionType === "undefined") return true;
  return ["link", "typed", "auto_bookmark", "reload"].includes(details.transitionType);
}

// Filters out background noise URLs (e.g. Google cookies, YouTube embeds)
// NOTE: KEEP ADDING MORE NOISE URLS IF FOUND (@nicovporta)
function isNoiseUrl(raw) {
  try {
    const u = new URL(raw);
    const host = u.hostname;
    const path = u.pathname;
    if (host === "accounts.google.com" && path === "/RotateCookiesPage") return true;
    if (host === "ogs.google.com") return true;
    if (host === "www.youtube.com" && path.startsWith("/embed")) return true;
  } catch (_) {}
  return false;
}