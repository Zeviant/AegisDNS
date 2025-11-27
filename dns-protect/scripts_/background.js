const BACKEND_URL = "http://127.0.0.1:5005";
let backendReachable = false;
let healthTimer = null;
let currentMode = "logging"; // 'logging' | 'silent' | 'safe' | 'none'
const safeAllowOnce = new Set(); // keys: `${tabId}|${url}`


// Load mode from storage on startup
chrome.storage.local.get(["mode"]).then(({ mode }) => {
  if (mode) {
    currentMode = mode;
  }
}).catch(() => {});

// Keep mode in sync with popup changes
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.mode) {
    currentMode = changes.mode.newValue || "logging";
  }
});

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

// LOGGING MODE
async function logNavigation(details) {
  if (currentMode !== "logging") return;
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

// SAFE MODE
// -- Blacklist managment 
async function checkBlacklist(details) {
  const url = details.url;

  // Don’t block internal extension pages 
  const extBase = chrome.runtime.getURL("");
  if (url.startsWith(extBase)) return false;
  if (isSearchUrl(url) || isNoiseUrl(url)) return false;

  // Ask backend if URL is blacklisted
  try {
    let response = await fetch(`${BACKEND_URL}/is_blacklisted`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    let data = await response.json();
    return data.blacklisted === true;
  } catch (e) {
    console.warn("Blacklist check failed:", e);
    return false;
  }
}

chrome.webNavigation.onBeforeNavigate.addListener(handleSafeModeNavigation, {
  url: [{ schemes: ["http", "https"] }],
});

async function handleSafeModeNavigation(details) {
  console.log("SAFE MODE TRIGGERED:", details.url);

  if (currentMode !== "safe") return;
  if (!isTopFrame(details)) return;

  const url = details.url;
  const extBase = chrome.runtime.getURL("");

  // Ignore extension pages & noise
  if (url.startsWith(extBase)) return;
  if (isSearchUrl(url) || isNoiseUrl(url)) return;

  const allowKey = `${details.tabId}|${url}`;
  if (safeAllowOnce.has(allowKey)) {
    safeAllowOnce.delete(allowKey);
    console.log("Safe allow-once hit, letting navigation pass:", url);
    return;
  }
  
  try {
    const resp = await fetch(`${BACKEND_URL}/is_blacklisted`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await resp.json();
    if (data.blacklisted) {
      console.log("URL is BLACKLISTED → showing RED warning page:", url);

      const warningUrl =
        `${chrome.runtime.getURL("html/blacklist_interstitial.html")}` +
        `?target=${encodeURIComponent(url)}`;

      chrome.tabs.update(details.tabId, { url: warningUrl }, () => {
        if (chrome.runtime.lastError) {
          console.error("REDIRECT ERROR (blacklist):", chrome.runtime.lastError.message);
        } else {
          console.log("Redirected to blacklist interstitial:", warningUrl);
        }
      });

      return;
    }
  } catch (e) {
    console.warn("Blacklist check failed:", e);
  }

  
  try {
    const resp = await fetch(`${BACKEND_URL}/is_whitelisted`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await resp.json();
    if (data.whitelisted) {
      console.log("URL is WHITELISTED → letting it pass:", url);
      return; 
    }
  } catch (e) {
    console.warn("Whitelist check failed:", e);
  }

  
  const interstitialUrl =
    `${chrome.runtime.getURL("html/safe_interstitial.html")}` +
    `?target=${encodeURIComponent(url)}`;

  try {
    await chrome.tabs.update(details.tabId, { url: interstitialUrl });
    console.log("Redirected to SAFE interstitial:", interstitialUrl);
  } catch (e) {
    console.warn("Failed to redirect to safe interstitial:", e);
  }
}


// // Intercept navigations and show interstitial
//     chrome.webNavigation.onBeforeNavigate.addListener((details) => {
//         return handleSafeModeNavigation(details);
//     }, {
//         url: [{ schemes: ["http", "https"] }],
//     });

// Handle messages from the safe interstitial page
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !sender || !sender.tab) {
    return;
  }

  const tabId = sender.tab.id;

  if (message.type === "safe-allow") {
    const targetUrl = message.targetUrl;
    if (targetUrl) {
      const allowKey = `${tabId}|${targetUrl}`;
      safeAllowOnce.add(allowKey);
      chrome.tabs.update(tabId, { url: targetUrl }, () => {
        void chrome.runtime.lastError;
      });
    }
    sendResponse && sendResponse({ ok: true });
    return true;
  }

  if (message.type === "safe-scan") {
    const targetUrl = message.targetUrl;
    if (targetUrl) {
      triggerScan(targetUrl).catch((e) => console.warn("Failed to trigger scan", e));
    }
    sendResponse && sendResponse({ ok: true });
    return true;
  }

  if (message.type === "safe-deny") {
    // If connection is rejected go back to previous site or close tab (if there is no previous site)
    chrome.tabs.goBack(tabId, () => {
      if (chrome.runtime.lastError) {
        chrome.tabs.remove(tabId).catch?.(() => {});
      }
    });
    sendResponse && sendResponse({ ok: true });
    return true;
  }

  // Buttons of blacklist page warning
  if (message.type === "blacklist-go-back") {
    chrome.tabs.goBack(tabId, () => {
      if (chrome.runtime.lastError) {
        chrome.tabs.remove(tabId).catch?.(() => {});
      }
    });
    sendResponse && sendResponse({ ok: true });
    return true;
  }

  if (message.type === "blacklist-continue") {
     const targetUrl = message.targetUrl;
    if (targetUrl) {
      const allowKey = `${tabId}|${targetUrl}`;
      safeAllowOnce.add(allowKey);
      chrome.tabs.update(tabId, { url: targetUrl }, () => {
        void chrome.runtime.lastError;
      });
    }
    sendResponse && sendResponse({ ok: true });
    return true;
  }

});

// Send scan request to app
async function triggerScan(targetUrl) {
  const ready = await ensureBackend();
  if (!ready) return;

  try {
    await fetch(`${BACKEND_URL}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: targetUrl,
        timestamp: Date.now(),
      }),
    });
  } catch (e) {
    console.warn("Failed to send scan request:", e);
  }
}

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