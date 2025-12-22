# --- Libraries ---
# Qt Libraries
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QProgressBar
import time

# Connection with service layer
from src.logic.vt_service import (
    _load_state,
    classify_kind,
    VTScanThread,
    VIRUSTOTAL_RATELIMIT
)

# --- Qt Presentation Functions ---
def render_vt_html(verdict: str, stats: dict) -> str:
    color = {"BLOCK": "#ef4444", "CAUTION": "#f59e0b", "SAFE": "#10b981"}.get(verdict, "#93a3b1")
    harmless = stats.get("harmless", 0)
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    undetected = stats.get("undetected", 0)
    timeout = stats.get("timeout", 0)
    return f"""
      <div style="font-family:'Segoe UI',Arial; font-size:14px; color:#e5e7eb;">
        <h2 style="margin:0 0 12px; font-size:22px; color:{color};">Verdict: {verdict}</h2>
        <table style="border-collapse:collapse; margin-top:6px;">
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Harmless</td>
              <td style="padding:4px 12px; font-weight:600;">{harmless}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Malicious</td>
              <td style="padding:4px 12px; font-weight:600;">{malicious}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Suspicious</td>
              <td style="padding:4px 12px; font-weight:600;">{suspicious}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Undetected</td>
              <td style="padding:4px 12px; font-weight:600;">{undetected}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Timeout</td>
              <td style="padding:4px 12px; font-weight:600;">{timeout}</td></tr>
        </table>
        <p style="margin-top:12px; color:#9aa5b1;">Source: VirusTotal (last_analysis_stats)</p>
      </div>
    """

def show_vt_box(parent, verdict: str, stats: dict):
    icon = (QMessageBox.Critical if verdict == "BLOCK"
            else QMessageBox.Warning if verdict == "CAUTION"
            else QMessageBox.Information)
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle("VirusTotal Result")
    box.setTextFormat(Qt.RichText)
    box.setText(render_vt_html(verdict, stats))
    box.setStandardButtons(QMessageBox.Ok)

    lbl = box.findChild(QLabel, "qt_msgbox_label")
    if lbl:
        lbl.setWordWrap(True)
        lbl.setMinimumSize(420, 260)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

    box.exec()

# Main Window (Where the user puts the input)
class Main_Window(QMainWindow):
    def __init__(self, userName, password, notify_callback=None):
        super().__init__()
        self.userName = userName 
        self.password = password
        self._notify_callback = notify_callback
        self._last_submitted_text = ""
        
        self.setWindowTitle(f"Main Window - User: {self.userName}")
        self.resize(400, 600)
        
        # Timer (UI state)
        self._cooldown_left = 0
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._cooldown_tick)

        # --- layout & style ---
        central = QWidget(self)
        self.setCentralWidget(central)
        page = QVBoxLayout(central)
        page.setContentsMargins(40, 40, 40, 40)

        # Load table styling from QSS file
        with open("src/gui/Style_Sheet/MainWindow_Style.qss", "r") as f:
            self.setStyleSheet(f.read())

        card = QFrame()
        card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(blurRadius=40, xOffset=0, yOffset=12)
        shadow.setColor(Qt.black)
        card.setGraphicsEffect(shadow)

        card_wrap = QVBoxLayout(card)
        card_wrap.setContentsMargins(48, 48, 48, 48)
        card_wrap.setSpacing(24)

        title = QLabel("ENTER A URL / DOMAIN / IP")
        tfont = QFont(); tfont.setPointSize(24); tfont.setBold(True)
        title.setFont(tfont); title.setAlignment(Qt.AlignHCenter)

        prompt = QLabel("Type a full URL, domain or an IP and click OK.")
        prompt.setAlignment(Qt.AlignHCenter)
        pfont = QFont(); pfont.setPointSize(11)
        prompt.setFont(pfont); prompt.setStyleSheet("color: #9aa5b1;")

        row = QHBoxLayout(); row.setSpacing(12)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Example: https://example.com  |  example.com  |  8.8.8.8")
        self.input_edit.setMinimumWidth(420)

        # Create the fake progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setObjectName("scanProgress")
        self._progress_accum = 0.0

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.on_ok)
        self.input_edit.returnPressed.connect(self.ok_btn.click)

        row.addWidget(self.input_edit, 1)
        row.addWidget(self.ok_btn)
        
        card_wrap.addWidget(title)
        card_wrap.addWidget(prompt)
        card_wrap.addLayout(row)
        card_wrap.addWidget(self.progress)

        page.addStretch(1)
        page.addWidget(card, 0, Qt.AlignHCenter)
        page.addStretch(1)

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(80)  # smooth animation
        self._progress_timer.timeout.connect(self._advance_progress)
        self._worker = None  

    def _advance_progress(self):
        value = self.progress.value()

        if value >= 95:
            return

        inc = 0.0
        if value < 30:
            inc = 2.0
        elif value < 50:
            inc = 1.0
        elif value < 70:
            inc = 0.6
        elif value < 95:
            inc = 0.3

        self._progress_accum += inc
        whole = int(self._progress_accum)
        if whole > 0:
            self._progress_accum -= whole
            self.progress.setValue(min(95, value + whole))

    # Cooldown Functions (UI Logic)
    def start_cooldown(self, seconds: int):
        self._cooldown_left = max(1, int(seconds))
        self.ok_btn.setEnabled(False)
        self.ok_btn.setText(f"Cooldown: {self._cooldown_left}s")
        self._cooldown_timer.start()

    def _cooldown_tick(self):
        self._cooldown_left -= 1
        if self._cooldown_left <= 0:
            self._cooldown_timer.stop()
            self.ok_btn.setEnabled(True)
            self.ok_btn.setText("OK")
        else:
            self.ok_btn.setText(f"Cooldown: {self._cooldown_left}s")

    def on_ok(self):
        raw = self.input_edit.text().strip()

        if not raw:
            QMessageBox.warning(self, "Empty input", "Please enter a URL, domain, or IP.")
            return

        # Remember last submitted text so we can reference it in notifications
        self._last_submitted_text = raw
        
        state = _load_state()
        last = float(state.get("last_call", 0) or 0)
        remaining = int(max(0, VIRUSTOTAL_RATELIMIT - (time.time() - last)))
        if remaining > 0:
            self.start_cooldown(remaining)
            return

        try:
            # Logic function call: uses imported classify_kind
            kind, target = classify_kind(raw)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return

        self.ok_btn.setEnabled(False)
        self.ok_btn.setText("Preparing...")

        self.progress.setValue(0)
        self.progress.setVisible(True)
        self._progress_accum = 0.0
        self._progress_timer.start()

        # Delegation of work to the imported service layer thread
        self._worker = VTScanThread(kind, target, self.userName, self)
        self._worker.tick.connect(self.on_cooldown_tick)
        self._worker.result.connect(self.on_result)
        self._worker.start()

    def on_cooldown_tick(self, secs_left: int):
        self.ok_btn.setText(f"Cooldown: {secs_left}s" if secs_left > 0 else "Scanning...")

    def on_result(self, payload: dict):
        self.ok_btn.setEnabled(True)
        self.ok_btn.setText("OK")
        self._progress_timer.stop()
        self.progress.setValue(100)

        QTimer.singleShot(300, lambda: (
            self.progress.setVisible(False),
            self.progress.setValue(0)
        ))

        if not payload.get("ok"):
            # The API key error message now comes from the logic layer
            QMessageBox.critical(self, "VirusTotal Error", payload.get("message", "Unknown error"))
            return

        stats = payload.get("stats", {}) or {}
        verdict = payload.get("verdict", "UNKNOWN")

        # Small delay so user can see bar getting filled up (CAN REMOVE LATER MAYBE) @NicoVegaPortaluppi
        QTimer.singleShot(200, lambda: show_vt_box(self, verdict, stats))
