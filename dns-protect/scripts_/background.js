const BACKEND_URL = "http://127.0.0.1:5005";
let backendReachable = false;
let healthTimer = null;
let currentMode = "logging"; // 'logging' | 'silent' | 'safe' | 'none'
const safeAllowOnce = new Set(); // keys: `${tabId}|${url}`

// Start ps
let packetSnifferWS = null;
let packetSnifferActive = false;
const SNIFFER_WS_PORT = 8765;
// End ps

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

// LOGGING & SILENT MODES
async function logNavigation(details) {
  if (currentMode !== "logging" && currentMode !== "silent") return;
  if (!isTopFrame(details)) return;
  if (!isAllowedTransition(details)) return;
  if (isSearchUrl(details.url)) return;
  if (isNoiseUrl(details.url)) return;
  const ready = await ensureBackend();
  if (!ready) return;

  const payloadMode = currentMode === "silent" ? "silent" : "logging";

  const payload = {
    url: details.url,
    timestamp: Date.now(),
    mode: payloadMode,
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

  // In silent mode, also trigger a background VT scan for this navigation.
  if (currentMode === "silent") {
    try {
      await triggerScan(details.url);
    } catch (e) {
      console.warn("Failed to trigger silent-mode scan:", e);
    }
  }
}

// Calls logNavigation when URL is loaded
chrome.webNavigation.onCompleted.addListener(logNavigation, {
  url: [{ schemes: ["http", "https"] }],
});

// SAFE MODE
// -- Blacklist managment 
async function checkBlacklist(details, signal) {
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
      signal,
    });

    let data = await response.json();
    return data.blacklisted === true;
  } catch (e) {
    console.warn("Blacklist check failed:", e);
    return false;
  }
}

async function checkWhitelist(details, signal) {
  const url = details.url;

  try {
    let response = await fetch(`${BACKEND_URL}/is_whitelisted`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal,
    });

    let data = await response.json();
    return data.whitelisted === true;
  } catch (e) {
    console.warn("Whitelist check failed:", e);
    return false;
  }
}

async function classifyUrl(details) {
  // Run blacklist + whitelist in parallel with a short timeout; default to unknown
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 800);
  try {
    const [isBlacklisted, isWhitelisted] = await Promise.all([
      checkBlacklist(details, controller.signal),
      checkWhitelist(details, controller.signal),
    ]);
    if (isBlacklisted) return "blacklisted";
    if (isWhitelisted) return "whitelisted";
    return "unknown";
  } catch (e) {
    if (e?.name !== "AbortError") {
      console.warn("Classification failed:", e);
    }
    return "unknown";
  } finally {
    clearTimeout(timeout);
  }
}

chrome.webNavigation.onBeforeNavigate.addListener(handleSafeModeNavigation, {
  url: [{ schemes: ["http", "https"] }],
});

chrome.webNavigation.onBeforeNavigate.addListener(handleGlobalBlacklistEnforcement, {
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

  // Log the navigation as a safe-mode event as soon as we intercept it.
  logSafeEvent(url, "interstitial").catch((e) =>
    console.warn("Failed to log safe interstitial event:", e)
  );
  
  // Start classification in parallel but redirect immediately to avoid the target page flashing.
  const pendingInterstitial =
    `${chrome.runtime.getURL("html/safe_interstitial.html")}` +
    `?target=${encodeURIComponent(url)}&pending=1`;

  chrome.tabs.update(details.tabId, { url: pendingInterstitial }).catch((e) => {
    console.warn("Failed to start interstitial redirect:", e);
  });

  const classification = await classifyUrl(details);

  if (classification === "blacklisted") {
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

  if (classification === "whitelisted") {
    console.log("URL is WHITELISTED → letting it pass:", url);
    // Avoid re-looping the navigation when we reload the target.
    const allowKey = `${details.tabId}|${url}`;
    safeAllowOnce.add(allowKey);
    try {
      await chrome.tabs.update(details.tabId, { url });
    } catch (e) {
      console.warn("Failed to continue to whitelisted URL:", e);
    }
    return;
  }

  // Default: keep the user on the safe interstitial (drop pending flag if desired)
  const finalInterstitial =
    `${chrome.runtime.getURL("html/safe_interstitial.html")}` +
    `?target=${encodeURIComponent(url)}`;
  if (finalInterstitial !== pendingInterstitial) {
    chrome.tabs.update(details.tabId, { url: finalInterstitial }).catch((e) => {
      console.warn("Failed to finalize safe interstitial:", e);
    });
  }
}

async function handleGlobalBlacklistEnforcement(details) {
  // Enforce blacklist in all modes except "none". Safe mode already handles it separately.
  if (currentMode === "none" || currentMode === "safe") return;
  if (!isTopFrame(details)) return;

  const url = details.url;
  const extBase = chrome.runtime.getURL("");
  if (url.startsWith(extBase)) return;
  if (isSearchUrl(url) || isNoiseUrl(url)) return;

  const allowKey = `${details.tabId}|${url}`;
  if (safeAllowOnce.has(allowKey)) {
    safeAllowOnce.delete(allowKey);
    return;
  }

  const isBlocked = await checkBlacklist(details);
  if (!isBlocked) return;

  const warningUrl =
    `${chrome.runtime.getURL("html/blacklist_interstitial.html")}` +
    `?target=${encodeURIComponent(url)}`;

  chrome.tabs.update(details.tabId, { url: warningUrl }, () => {
    if (chrome.runtime.lastError) {
      console.error("REDIRECT ERROR (global blacklist):", chrome.runtime.lastError.message);
    }
  });
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

  if (message.type === "safe-whitelist") {
    const targetUrl = message.targetUrl;
    (async () => {
      try {
        await addListEntry("whitelist", targetUrl);
        const allowKey = `${tabId}|${targetUrl}`;
        safeAllowOnce.add(allowKey);
        await chrome.tabs.update(tabId, { url: targetUrl });
        sendResponse && sendResponse({ ok: true });
      } catch (e) {
        sendResponse && sendResponse({ ok: false, reason: e?.message || "Failed" });
      }
    })();
    return true;
  }

  if (message.type === "safe-blacklist") {
    const targetUrl = message.targetUrl;
    (async () => {
      try {
        await addListEntry("blacklist", targetUrl);
        const warningUrl =
          `${chrome.runtime.getURL("html/blacklist_interstitial.html")}` +
          `?target=${encodeURIComponent(targetUrl)}`;
        await chrome.tabs.update(tabId, { url: warningUrl });
        sendResponse && sendResponse({ ok: true });
      } catch (e) {
        sendResponse && sendResponse({ ok: false, reason: e?.message || "Failed" });
      }
    })();
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

async function addListEntry(kind, targetUrl) {
  if (!targetUrl) throw new Error("Missing URL");
  const ready = await ensureBackend();
  if (!ready) throw new Error("App backend unreachable");

  const endpoint =
    kind === "whitelist" ? "add_to_whitelist" : "add_to_blacklist";

  const resp = await fetch(`${BACKEND_URL}/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: targetUrl,
      source: "extension",
    }),
  });

  let data = null;
  try {
    data = await resp.json();
  } catch (_) {}

  if (!resp.ok || data?.ok !== true) {
    throw new Error(data?.reason || "Request failed");
  }

  return data;
}

async function logSafeEvent(targetUrl, action) {
  const ready = await ensureBackend();
  if (!ready) return;

  const payload = {
    url: targetUrl,
    timestamp: Date.now(),
    mode: "safe",
    action: action || "interstitial",
  };

  try {
    await fetch(`${BACKEND_URL}/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("Failed to log safe event:", err);
  }
}

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

// Start ps
function handlePacketSnifferMessage(data) {
  // Store packet in storage for popup to access
  chrome.storage.local.get(['packetLogs'], (result) => {
    const logs = result.packetLogs || [];
    logs.push({
      ...data,
      timestamp: Date.now()
    });
    
    // Keep only last 1000 packets
    if (logs.length > 1000) {
      logs.splice(0, logs.length - 1000);
    }
    
    chrome.storage.local.set({ packetLogs: logs });
    
    // Notify popup if it's open
    chrome.runtime.sendMessage({
      type: 'packetUpdate',
      packet: data
    }).catch(() => {}); // Ignore if no popup is open
  });
}

// Add this function to start packet sniffer
async function startPacketSniffer(interface = null) {
  if (packetSnifferActive) {
    return { status: 'already_running' };
  }
  
  try {
    // Start via Flask API
    const response = await fetch(`${BACKEND_URL}/sniffer/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interface })
    });
    
    const data = await response.json();
    
    if (data.status === 'started') {
      // Connect to WebSocket for real-time updates
      connectToPacketSnifferWS();
      packetSnifferActive = true;
      
      // Update badge to show sniffer is active
      chrome.action.setBadgeText({ text: '📡' });
      chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
    }
    
    return data;
  } catch (error) {
    console.warn('Failed to start packet sniffer:', error);
    return { status: 'error', message: error.message };
  }
}

// Add this function to stop packet sniffer
async function stopPacketSniffer() {
  if (!packetSnifferActive) {
    return { status: 'not_running' };
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/sniffer/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    
    if (data.status === 'stopped') {
      packetSnifferActive = false;
      
      // Disconnect WebSocket
      if (packetSnifferWS) {
        packetSnifferWS.close();
        packetSnifferWS = null;
      }
      
      // Clear badge
      chrome.action.setBadgeText({ text: '' });
    }
    
    return data;
  } catch (error) {
    console.warn('Failed to stop packet sniffer:', error);
    return { status: 'error', message: error.message };
  }
}

// Add this function to connect to WebSocket
function connectToPacketSnifferWS() {
  if (packetSnifferWS) {
    packetSnifferWS.close();
  }
  
  packetSnifferWS = new WebSocket(`ws://localhost:${SNIFFER_WS_PORT}`);
  
  packetSnifferWS.onopen = () => {
    console.log('Packet sniffer WebSocket connected');
  };
  
  packetSnifferWS.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'packet') {
        handlePacketSnifferMessage(data.data);
      }
    } catch (error) {
      console.warn('Failed to parse packet message:', error);
    }
  };
  
  packetSnifferWS.onclose = () => {
    console.log('Packet sniffer WebSocket disconnected');
    packetSnifferWS = null;
    
    // Try to reconnect if still supposed to be active
    if (packetSnifferActive) {
      setTimeout(() => connectToPacketSnifferWS(), 3000);
    }
  };
  
  packetSnifferWS.onerror = (error) => {
    console.warn('Packet sniffer WebSocket error:', error);
  };
}

// Add this function to get sniffer status
async function getSnifferStatus() {
  try {
    const response = await fetch(`${BACKEND_URL}/sniffer/status`);
    return await response.json();
  } catch (error) {
    return { running: false, error: error.message };
  }
}

// Add this function to get interfaces
async function getSnifferInterfaces() {
  try {
    const response = await fetch(`${BACKEND_URL}/sniffer/interfaces`);
    return await response.json();
  } catch (error) {
    return { interfaces: [] };
  }
}

// Add this function to get captured packets
async function getSnifferPackets() {
  try {
    const response = await fetch(`${BACKEND_URL}/sniffer/packets`);
    return await response.json();
  } catch (error) {
    return { packets: [] };
  }
}

// Update pingBackend to check sniffer status
async function pingBackend() {
  try {
    const res = await fetch(`${BACKEND_URL}/health`, { cache: "no-store" });
    backendReachable = res.ok;
    const data = backendReachable ? await res.json() : null;
    
    // Check sniffer status if backend is reachable
    if (backendReachable && data.sniffer_running) {
      packetSnifferActive = data.sniffer_running;
      if (!packetSnifferWS) {
        connectToPacketSnifferWS();
      }
    }
    
    await chrome.storage.session.set({ 
      backendReachable, 
      health: data,
      packetSnifferActive 
    });
  } catch (e) {
    console.warn("Application backend unreachable:", e);
    backendReachable = false;
    packetSnifferActive = false;
    await chrome.storage.session.set({ 
      backendReachable, 
      health: null,
      packetSnifferActive: false 
    });
  }
  scheduleHealthPolling();
  return backendReachable;
}

// Add message listener for packet sniffer commands
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // ... (your existing message handlers)
  
  // Add packet sniffer handlers
  if (message.type === 'startSniffer') {
    startPacketSniffer(message.interface)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ status: 'error', message: error.message }));
    return true;
  }
  
  if (message.type === 'stopSniffer') {
    stopPacketSniffer()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ status: 'error', message: error.message }));
    return true;
  }
  
  if (message.type === 'getSnifferStatus') {
    getSnifferStatus()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ running: false, error: error.message }));
    return true;
  }
  
  if (message.type === 'getSnifferInterfaces') {
    getSnifferInterfaces()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ interfaces: [] }));
    return true;
  }
  
  if (message.type === 'getSnifferPackets') {
    getSnifferPackets()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ packets: [] }));
    return true;
  }
  
  // Handle packet updates from popup
  if (message.type === 'packetUpdate') {
    handlePacketSnifferMessage(message.packet);
    sendResponse({ ok: true });
    return true;
  }
});

// Add cleanup on extension unload
chrome.runtime.onSuspend.addListener(() => {
  if (packetSnifferWS) {
    packetSnifferWS.close();
  }
  
  if (packetSnifferActive) {
    // Try to stop sniffer gracefully
    fetch(`${BACKEND_URL}/sniffer/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }).catch(() => {}); // Ignore errors during shutdown
  }
});
// End ps