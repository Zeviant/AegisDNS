"""
GUI-side scanner service.

The actual scan logic (WHOIS/DNS/TLS/HTTP heuristics) now runs in the backend
container (see backend/services/scanner_service.py) — this module keeps the same
public names the GUI already imports (`risk_score_to_verdict`, `ScannerScanThread`)
so Scanner_Window.py / main_window.py need no changes beyond what already talks to
these names. ScannerScanThread.run() now calls the backend over HTTP instead of
running the scan in-process.
"""
from PySide6.QtCore import QThread, Signal

from src.logic import api_client


def risk_score_to_verdict(risk_score: int) -> str:
    if risk_score >= 60:
        return "MALICIOUS"
    elif risk_score >= 50:
        return "DANGEROUS"
    elif risk_score >= 40:
        return "SUSPICIOUS"
    elif risk_score >= 30:
        return "CAUTION"
    elif risk_score >= 20:
        return "NEUTRAL"
    elif risk_score >= 10:
        return "SAFE"
    else:
        return "SECURE"


class ScannerScanThread(QThread):
    result = Signal(dict)
    tick = Signal(int)

    def __init__(self, kind: str, target: str, userName: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.target = target
        self.userName = userName

    def run(self):
        try:
            self.tick.emit(0)
            payload = api_client.scan_local(self.kind, self.target, self.userName)
            self.result.emit(payload)
        except api_client.BackendUnavailable as e:
            self.result.emit({"ok": False, "message": f"Backend unavailable: {e}"})
        except Exception as e:
            self.result.emit({"ok": False, "message": f"Scanner error: {e}"})
