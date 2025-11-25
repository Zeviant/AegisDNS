const targetLabel = document.getElementById("targetLabel");
const allowBtn = document.getElementById("allowBtn");
const scanBtn = document.getElementById("scanBtn");
const denyBtn = document.getElementById("denyBtn");

// Extract target URL from query parameters
const params = new URLSearchParams(window.location.search);
const targetUrl = params.get("target") || "";

if (targetLabel) {
  if (targetUrl) {
    targetLabel.textContent = `Target: ${targetUrl}`;
  } else {
    targetLabel.textContent = "No target URL detected.";
  }
}

// ALLOW
allowBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "safe-allow", targetUrl });
});

// SCAN
let scanLocked = false;
scanBtn.addEventListener("click", () => {
  if (scanLocked) return;
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
denyBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "safe-deny", targetUrl });
});
