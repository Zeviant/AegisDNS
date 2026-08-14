import os
import json
import threading
from datetime import datetime
from pathlib import Path

import requests

# MODEL_DIR is env-configurable. The original GUI-side code fell back to
# Windows' APPDATA env var, which doesn't exist on Linux — the container always
# gets an explicit MODEL_DIR (pointed at a mounted volume so the ~2GB model
# survives container recreation instead of being re-downloaded every time).
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(Path.home() / "AeghisDNS" / "models")))
MODEL_PATH = MODEL_DIR / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODEL_URL = (
    "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF"
    "/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CACHE_DIR = os.path.join(_BACKEND_DIR, "VT_Cache")
CACHE_DIR = os.getenv("VT_CACHE_DIR", _DEFAULT_CACHE_DIR)
os.makedirs(CACHE_DIR, exist_ok=True)
# Same scanner cache file scanner_service.py writes to — AI overviews are attached
# to existing scan cache entries.
_SCANNER_CACHE_FILE = Path(CACHE_DIR) / "scanner_cache.json"

_SYSTEM_PROMPT = """\
You are AeghisDNS, a security assistant built into a browsing scanner. \
Your job is to explain scan results to everyday users — not security experts.

Rules:
- Focus only on the most impactful signals. Signals below ±3 are noise and will not be provided.
- If the verdict is SAFE or SECURE, do not mention minor imperfections — focus on why the site is trustworthy. A low overall score outweighs any small individual issue.
- If the verdict is DANGEROUS or MALICIOUS, lead with the most harmful signals and explain the real-world risk to the user.
- Explain WHY each signal matters in real-world terms — what could actually happen to the user.
- Never use unexplained technical jargon.
- Write in plain prose. No bullet points, no lists.
- Keep the explanation to 5 sentences maximum.
- Never say a site "is safe" or "is secure" with certainty. Always use hedged language: "appears to be", "seems safe", "looks trustworthy".
- End with exactly one sentence on a new line starting with RECOMMENDATION:\
"""

_EXAMPLE_USER = """\
Verdict: DANGEROUS
Risk Score: 55

Signals:
- tls_certificate: +15 (No HTTPS certificate; site served over HTTP only)
- dns_mail: +6 (No MX records; No SPF record; No DMARC policy)
- privacy: +3 (Privacy protection detected on WHOIS)
- domain_age: 0 (Domain age does not indicate any particular risk)
- registrar: 0 (Registrar does not indicate malicious activity)\
"""

_EXAMPLE_ASSISTANT = """\
This website does not use HTTPS, meaning anything you type — passwords, personal details, \
payment info — travels in plain unencrypted text that anyone on the same network could intercept. \
It also has no email infrastructure set up whatsoever, which every legitimate business has, \
suggesting nobody professionally operates this site. The owner's identity is also deliberately hidden.

RECOMMENDATION: Avoid entering any personal information on this site, and think twice before visiting it until you can verify who runs it.\
"""

_EXAMPLE_USER_SAFE = """\
Verdict: SAFE
Risk Score: 8

Positive indicators:
- domain_age: -10 (Domain is over 10 years old)
- dns_mail: -6 (MX, SPF, and DMARC all present)
- domain_expiration: -7 (Domain expiry is well into the future)\
"""

_EXAMPLE_ASSISTANT_SAFE = """\
This website has been active for over a decade and has all email security properly configured, \
which are strong signs of a legitimate, professionally maintained site. \
The overall risk score is very low and no red flags were found.

RECOMMENDATION: This site appears to be safe to use normally.\
"""


def _cache_key(kind: str, target: str) -> str:
    kind = (kind or "").lower()
    if kind == "url":
        norm = target if target.lower().startswith(("http://", "https://")) else f"http://{target}"
        return f"url:{norm}"
    return f"{kind}:{target}"


def get_cached_ai_overview(kind: str, target: str) -> dict | None:
    """Return {'explanation', 'recommendation'} if cached, else None."""
    try:
        if not _SCANNER_CACHE_FILE.exists():
            return None
        with open(_SCANNER_CACHE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        cache = state.get("cache", {}) or {}
        entry = cache.get(_cache_key(kind, target))
        if not entry:
            return None
        return entry.get("ai_overview")
    except Exception:
        return None


def save_ai_overview(kind: str, target: str, explanation: str, recommendation: str) -> None:
    """Attach AI overview to the existing scanner cache entry for this target."""
    try:
        state = {"last_call": 0, "cache": {}}
        if _SCANNER_CACHE_FILE.exists():
            with open(_SCANNER_CACHE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        cache = state.setdefault("cache", {})
        entry = cache.setdefault(_cache_key(kind, target), {})
        entry["ai_overview"] = {
            "explanation": explanation,
            "recommendation": recommendation,
            "ts": datetime.now().isoformat(),
        }
        tmp = str(_SCANNER_CACHE_FILE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, _SCANNER_CACHE_FILE)
    except Exception:
        pass


def model_is_downloaded() -> bool:
    return MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 100_000_000


_llm_instance = None
_llm_lock = threading.Lock()


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        with _llm_lock:
            if _llm_instance is None:
                from llama_cpp import Llama
                _llm_instance = Llama(
                    model_path=str(MODEL_PATH),
                    n_ctx=2048,
                    n_threads=10,
                    verbose=False,
                )
    return _llm_instance


def _build_prompt(verdict: str, stats: dict, signals: list) -> str:
    risk_score = stats.get("risk_score", 0)

    risk_lines = []
    good_lines = []

    for s in signals:
        score = s.get("risk_score", 0)
        name = s.get("name", "unknown")
        reason = s.get("reason", "")

        if score >= 3:
            line = f"- {name}: +{score}"
            if reason:
                line += f" ({reason})"
            risk_lines.append(line)
        elif score <= -3:
            line = f"- {name}: {score}"
            if reason:
                line += f" ({reason})"
            good_lines.append(line)

    sections = []
    if good_lines:
        sections.append("Positive indicators:\n" + "\n".join(good_lines))
    if risk_lines:
        sections.append("Risk signals:\n" + "\n".join(risk_lines))
    if not sections:
        sections.append("No significant signals detected.")

    return f"Verdict: {verdict}\nRisk Score: {risk_score}\n\n" + "\n\n".join(sections)


def run_ai_overview(verdict: str, stats: dict, signals: list, kind: str = "", target: str = "") -> dict:
    """
    Synchronous AI overview generation — same logic that used to live in
    LLMExplainThread.run(), minus the QThread/Signal plumbing.
    """
    if kind and target:
        cached = get_cached_ai_overview(kind, target)
        if cached:
            return {"ok": True, "explanation": cached.get("explanation", ""),
                     "recommendation": cached.get("recommendation", "")}

    if not model_is_downloaded():
        return {"ok": False, "message": "Model not downloaded", "model_missing": True}

    try:
        llm = _get_llm()
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _EXAMPLE_USER},
                {"role": "assistant", "content": _EXAMPLE_ASSISTANT},
                {"role": "user", "content": _EXAMPLE_USER_SAFE},
                {"role": "assistant", "content": _EXAMPLE_ASSISTANT_SAFE},
                {"role": "user", "content": _build_prompt(verdict, stats, signals)},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        raw = response["choices"][0]["message"]["content"].strip()

        if "RECOMMENDATION:" in raw:
            parts = raw.split("RECOMMENDATION:", 1)
            explanation = parts[0].strip()
            recommendation = parts[1].strip()
        else:
            explanation = raw
            recommendation = ""

        if kind and target:
            save_ai_overview(kind, target, explanation, recommendation)

        return {"ok": True, "explanation": explanation, "recommendation": recommendation}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# --- Model download, tracked in a module-level dict and polled over HTTP ---
# (replaces ModelDownloadThread's `progress`/`finished` Qt signals — a plain
# background thread here updates _download_state, and GET /ai/model/download/
# progress reports it).
_download_state = {"active": False, "percent": 0, "downloaded_mb": 0.0,
                    "total_mb": 0.0, "done": False, "error": None}
_download_lock = threading.Lock()


def get_download_progress() -> dict:
    with _download_lock:
        return dict(_download_state)


def _download_worker():
    global _download_state
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = MODEL_PATH.with_suffix(".gguf.tmp")
    try:
        response = requests.get(MODEL_URL, stream=True, timeout=30, allow_redirects=True)
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    with _download_lock:
                        _download_state["downloaded_mb"] = downloaded / 1e6
                        if total:
                            _download_state["total_mb"] = total / 1e6
                            _download_state["percent"] = int(downloaded / total * 100)
        tmp_path.rename(MODEL_PATH)
        with _download_lock:
            _download_state["active"] = False
            _download_state["done"] = True
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        with _download_lock:
            _download_state["active"] = False
            _download_state["error"] = str(e)


def start_model_download() -> dict:
    with _download_lock:
        if _download_state["active"]:
            return {"ok": False, "message": "Download already in progress"}
        _download_state.update({"active": True, "percent": 0, "downloaded_mb": 0.0,
                                 "total_mb": 0.0, "done": False, "error": None})
    threading.Thread(target=_download_worker, daemon=True).start()
    return {"ok": True}
