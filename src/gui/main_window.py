# --- Libraries ---
# Qt Libraries
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import os, sys, time

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
        self.resize(450, 450)
        
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

        central.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0,y1:0, x2:0,y2:1,
                    stop:0 #0f172a, stop:1 #0b1220);
                color: #e5e7eb;
                font-size: 14px;
            }
        """)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card { background: #101e29; border-radius: 16px; }
            QLineEdit {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 10px;
                padding: 10px 12px;
                color: #e5e7eb;
                selection-background-color: #1e40af;
            }
            QLineEdit:focus { border: 1px solid #60a5fa; background: rgba(255,255,255,0.09); }
            QPushButton {
                border: none; border-radius: 10px; padding: 10px 16px;
                background: #1d4ed8; color: white; font-weight: 600;
            }
            QPushButton:hover { background: #2563eb; }
            QPushButton:disabled { background: #334155; color: #cbd5e1; }
            QPushButton:pressed { background: #1e40af; }
        """)
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

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.on_ok)
        self.input_edit.returnPressed.connect(self.ok_btn.click)

        row.addWidget(self.input_edit, 1)
        row.addWidget(self.ok_btn)

        card_wrap.addWidget(title)
        card_wrap.addWidget(prompt)
        card_wrap.addLayout(row)

        page.addStretch(1)
        page.addWidget(card, 0, Qt.AlignHCenter)
        page.addStretch(1)

        self._worker = None  

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

        if not payload.get("ok"):
            # The API key error message now comes from the logic layer
            QMessageBox.critical(self, "VirusTotal Error", payload.get("message", "Unknown error"))
            return

        stats = payload.get("stats", {}) or {}
        verdict = payload.get("verdict", "UNKNOWN")

        # Send system notification
        if self._notify_callback:
            try:
                self._notify_callback(verdict, self._last_submitted_text)
            except Exception:
                pass

        show_vt_box(self, verdict, stats)