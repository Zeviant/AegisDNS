const statusLabel = document.getElementById("statusLabel");
const modePanel = document.getElementById("modePanel");
const modeButtons = Array.from(document.querySelectorAll(".mode"));
const hint = document.querySelector(".hint");

// Change label text depending on server condition
function setStatus(isConnected) {
  statusLabel.textContent = isConnected ? "Connected" : "Disconnected";
}

function applyModeUI(mode) {
  modeButtons.forEach((btn) => {
    const btnMode = btn.dataset.mode;
    if (btnMode === mode) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  if (!hint) return;

  switch (mode) {
    case "logging":
      hint.textContent = "Logging: Navigations are recorded to the app. No blocking or automatic scans.";
      break;
    case "silent":
      hint.textContent = "Silent: Navigations are being recorded and scanned automatically.";
      break;
    case "safe":
      hint.textContent = "Safe: Navigations are being intercepted. User must manually allow or deny each connection.";
      break;
    case "none":
    default:
      hint.textContent = "None: Extension is disabled.";
      break;
  }
}

async function initPopup() {
  // Connectivity indicator
  const { backendReachable } = await chrome.storage.session.get(["backendReachable"]);
  setStatus(Boolean(backendReachable));

  // Initialize mode state from storage (default: logging)
  const stored = await chrome.storage.local.get(["mode"]);
  const currentMode = stored.mode || "logging";
  applyModeUI(currentMode);

  // Set up buttons
  modeButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const newMode = btn.dataset.mode;
      await chrome.storage.local.set({ mode: newMode });
      applyModeUI(newMode);
    });
  });
}

// Runs when popup opens
document.addEventListener("DOMContentLoaded", () => {
  initPopup().catch((e) => console.error("Popup init failed", e));
});

// Runs while popup is open and checks server connectivity every time it changes
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "session" && "backendReachable" in changes) {
    chrome.storage.session.get(["backendReachable"]).then(({ backendReachable }) => {
      setStatus(Boolean(backendReachable));
    });
  }
});