const targetLabel = document.getElementById("targetLabel");
const statusLabel = document.getElementById("statusLabel");
const allowBtn = document.getElementById("allowBtn");
const scanBtn = document.getElementById("scanBtn");
const denyBtn = document.getElementById("denyBtn");
const whitelistBtn = document.getElementById("whitelistBtn");
const blacklistBtn = document.getElementById("blacklistBtn");

// Extract target URL from query parameters
const params = new URLSearchParams(window.location.search);
const targetUrl = params.get("target") || "";
const pendingCheck = params.get("pending") === "1";

function setStatus(text) {
  if (statusLabel && text) {
    statusLabel.textContent = text;
  }
}

if (targetLabel) {
  if (targetUrl) {
    targetLabel.textContent = targetUrl;
  } else {
    targetLabel.textContent = "No target URL detected.";
  }
}

if (pendingCheck) {
  setStatus("Checking site against lists…");
}

function withButtonLock(button, workingText, fn) {
  return async () => {
    if (!button || button.disabled) return;
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = workingText;
    try {
      await fn();
    } catch (e) {
      console.warn(e);
      setStatus("Something went wrong. Try again.");
    } finally {
      // Keep button disabled if navigation is expected; otherwise restore.
      if (!document.hidden) {
        button.disabled = false;
        button.textContent = originalText;
      }
    }
  };
}

// ALLOW
allowBtn?.addEventListener(
  "click",
  withButtonLock(allowBtn, "Continuing…", async () => {
    setStatus("Continuing to site…");
    await chrome.runtime.sendMessage({ type: "safe-allow", targetUrl });
  })
);

// SCAN
let scanLocked = false;
scanBtn?.addEventListener("click", () => {
  if (scanLocked || !scanBtn) return;
  scanLocked = true;

  const originalText = scanBtn.textContent;
  scanBtn.disabled = true;
  scanBtn.textContent = "Scan sent";

  chrome.runtime.sendMessage({ type: "safe-scan", targetUrl });

  // Re-enable after 30 seconds to prevent spamming
  setTimeout(() => {
    scanLocked = false;
    scanBtn.disabled = false;
    scanBtn.textContent = originalText;
  }, 30000);
});

// DENY
denyBtn?.addEventListener(
  "click",
  withButtonLock(denyBtn, "Going back…", async () => {
    await chrome.runtime.sendMessage({ type: "safe-deny", targetUrl });
  })
);

// WHITELIST
whitelistBtn?.addEventListener(
  "click",
  withButtonLock(whitelistBtn, "Whitelisting…", async () => {
    if (!targetUrl) {
      setStatus("No target URL detected.");
      return;
    }
    const res = await chrome.runtime.sendMessage({ type: "safe-whitelist", targetUrl });
    if (!res?.ok) {
      setStatus(res?.reason || "Failed to whitelist.");
      return;
    }
    setStatus("Whitelisted. Opening site…");
  })
);

// BLACKLIST
blacklistBtn?.addEventListener(
  "click",
  withButtonLock(blacklistBtn, "Blacklisting…", async () => {
    if (!targetUrl) {
      setStatus("No target URL detected.");
      return;
    }
    const res = await chrome.runtime.sendMessage({ type: "safe-blacklist", targetUrl });
    if (!res?.ok) {
      setStatus(res?.reason || "Failed to blacklist.");
      return;
    }
    setStatus("Blocked and redirecting…");
  })
);
