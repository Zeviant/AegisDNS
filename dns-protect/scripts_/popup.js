const statusLabel = document.getElementById("statusLabel");
const modePanel = document.getElementById("modePanel");

// Change label text depending on server condition
function setStatus(isConnected) {
  statusLabel.textContent = isConnected ? "Connected" : "Disconnected";
}

// Runs when popup opens and checks server connectivity
document.addEventListener("DOMContentLoaded", async () => {
  const { backendReachable } = await chrome.storage.session.get(["backendReachable"]);
  setStatus(Boolean(backendReachable));
});

// Runs while popup is open and checks server connectivity every time it changes
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "session") return;
  if ("backendReachable" in changes) {
    chrome.storage.session.get(["backendReachable"]).then(({ backendReachable }) => {
      setStatus(Boolean(backendReachable));
    });
  }
});