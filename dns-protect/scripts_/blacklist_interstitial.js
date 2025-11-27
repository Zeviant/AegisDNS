// Extract the URL the user attempted to visit
const urlParams = new URLSearchParams(window.location.search);
const targetUrl = urlParams.get("target");

const goBackBtn = document.getElementById("goBackBtn");
const continueBtn = document.getElementById("continueBtn");

// Show the URL
document.getElementById("url").textContent = targetUrl;

// GO BACK
goBackBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "blacklist-go-back", targetUrl });
});

// CONTINUE ANYWAY
continueBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "blacklist-continue", targetUrl });
});
