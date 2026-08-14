"""
GUI-side AI overview / model download service.

Model inference and the ~2GB model file now live in the backend container (see
backend/services/llm_service.py) — this module keeps the same public names the
GUI already imports (Scanner_Window.py, history_window.py, model_download_dialog.py)
so only what happens inside these functions changed (HTTP call instead of local
llama.cpp inference / local model file).
"""
import time

from PySide6.QtCore import QThread, Signal

from src.logic import api_client


def get_cached_ai_overview(kind: str, target: str) -> dict | None:
    return api_client.get_cached_ai_overview(kind, target)


def model_is_downloaded() -> bool:
    try:
        return bool(api_client.model_status().get("downloaded"))
    except api_client.BackendUnavailable:
        return False


class ModelDownloadThread(QThread):
    progress = Signal(int, float, float)  # percent, downloaded_mb, total_mb
    finished = Signal(bool, str)          # success, error_message

    def run(self):
        try:
            started = api_client.start_model_download()
            if not started.get("ok"):
                self.finished.emit(False, started.get("message", "Failed to start download"))
                return

            while True:
                time.sleep(1)
                state = api_client.get_download_progress()
                self.progress.emit(
                    int(state.get("percent", 0)),
                    float(state.get("downloaded_mb", 0.0)),
                    float(state.get("total_mb", 0.0)),
                )
                if state.get("done"):
                    self.finished.emit(True, "")
                    return
                if state.get("error"):
                    self.finished.emit(False, state.get("error"))
                    return
                if not state.get("active") and not state.get("done"):
                    # Download isn't active and didn't report done/error — treat as failure
                    # rather than polling forever.
                    self.finished.emit(False, "Download stopped unexpectedly")
                    return
        except api_client.BackendUnavailable as e:
            self.finished.emit(False, f"Backend unavailable: {e}")
        except Exception as e:
            self.finished.emit(False, str(e))


class LLMExplainThread(QThread):
    result = Signal(dict)

    def __init__(self, verdict: str, stats: dict, signals: list,
                 kind: str = "", target: str = "", parent=None):
        super().__init__(parent)
        self._verdict = verdict
        self._stats = stats
        self._signals = signals
        self._kind = kind
        self._target = target

    def run(self):
        try:
            response = api_client.ai_overview(
                self._verdict, self._stats, self._signals, kind=self._kind, target=self._target,
            )
            self.result.emit(response)
        except api_client.BackendUnavailable as e:
            self.result.emit({"ok": False, "message": f"Backend unavailable: {e}"})
        except Exception as e:
            self.result.emit({"ok": False, "message": str(e)})
