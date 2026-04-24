import os
import requests
from pathlib import Path
from PySide6.QtCore import QThread, Signal

MODEL_DIR = Path(os.getenv("APPDATA", Path.home())) / "AeghisDNS" / "models"
MODEL_PATH = MODEL_DIR / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODEL_URL = (
    "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF"
    "/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
)

_llm_instance = None

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

# Few-shot example injected as a prior conversation turn so the model
# learns the expected format from a concrete case.
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


def model_is_downloaded() -> bool:
    return MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 100_000_000


def _get_llm():
    global _llm_instance
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

    return (
        f"Verdict: {verdict}\n"
        f"Risk Score: {risk_score}\n\n"
        + "\n\n".join(sections)
    )


class ModelDownloadThread(QThread):
    progress = Signal(int, float, float)  # percent, downloaded_mb, total_mb
    finished = Signal(bool, str)          # success, error_message

    def run(self):
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
                        if total:
                            percent = int(downloaded / total * 100)
                            self.progress.emit(percent, downloaded / 1e6, total / 1e6)
            tmp_path.rename(MODEL_PATH)
            self.finished.emit(True, "")
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            self.finished.emit(False, str(e))


class LLMExplainThread(QThread):
    result = Signal(dict)

    def __init__(self, verdict: str, stats: dict, signals: list, parent=None):
        super().__init__(parent)
        self._verdict = verdict
        self._stats = stats
        self._signals = signals

    def run(self):
        try:
            llm = _get_llm()
            response = llm.create_chat_completion(
                messages=[
                    {"role": "system",    "content": _SYSTEM_PROMPT},
                    {"role": "user",      "content": _EXAMPLE_USER},
                    {"role": "assistant", "content": _EXAMPLE_ASSISTANT},
                    {"role": "user",      "content": _EXAMPLE_USER_SAFE},
                    {"role": "assistant", "content": _EXAMPLE_ASSISTANT_SAFE},
                    {"role": "user",      "content": _build_prompt(self._verdict, self._stats, self._signals)},
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

            self.result.emit({
                "ok": True,
                "explanation": explanation,
                "recommendation": recommendation,
            })
        except Exception as e:
            self.result.emit({"ok": False, "message": str(e)})
