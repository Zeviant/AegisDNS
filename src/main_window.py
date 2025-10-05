# Importando librerias importantes
import os, sys, time, base64, requests

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect,
    QStackedWidget
)
from PySide6.QtGui import QRegularExpressionValidator, QFont
from PySide6.QtCore import QRegularExpression, Qt, QThread, Signal

# Importando load_dotenv, it read the .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Normalizando la url
def url_to_vt_id(url: str) -> str:
    """VirusTotal URL ID is base64url of the URL without '=' padding."""
    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii")
    return b64.strip("=")


#  Styled VT result helpers 
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

# Virus Total Resutls box
def show_vt_box(parent, verdict: str, stats: dict):
    icon = (QMessageBox.Critical if verdict == "BLOCK"
            else QMessageBox.Warning if verdict == "CAUTION"
            else QMessageBox.Information)
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle("VirusTotal Result")
    box.setTextFormat(Qt.RichText)                 # enable HTML
    box.setText(render_vt_html(verdict, stats))
    box.setStandardButtons(QMessageBox.Ok)

    # Make content bigger + wrapped + selectable
    lbl = box.findChild(QLabel, "qt_msgbox_label")
    if lbl:
        lbl.setWordWrap(True)
        lbl.setMinimumSize(250, 200)             
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

    box.exec()



class VTUrlScanThread(QThread):
    result = Signal(dict)  # emits {"ok": True/False, "message": str, "stats": {...}, "verdict": str}
    def __init__(self, url: str, api_key: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.api_key = api_key
        self.base = "https://www.virustotal.com/api/v3"
        self.headers = {"x-apikey": self.api_key}

    def run(self):
        try:
            # 1) Submit URL for analysis
            resp = requests.post(
                f"{self.base}/urls",
                headers=self.headers,
                data={"url": self.url},
                timeout=15,
            )
            if resp.status_code not in (200, 201):
                self.result.emit({"ok": False, "message": f"Submit failed: {resp.status_code} {resp.text}"})
                return
            analysis_id = resp.json()["data"]["id"]

            # 2) Poll analysis until completed
            for _ in range(30):  # up to ~30s
                r = requests.get(f"{self.base}/analyses/{analysis_id}", headers=self.headers, timeout=15)
                if r.status_code != 200:
                    time.sleep(1); continue
                status = r.json().get("data", {}).get("attributes", {}).get("status", "")
                if status == "completed":
                    break
                time.sleep(1)
            else:
                self.result.emit({"ok": False, "message": "Timed out waiting for VirusTotal analysis to complete."})
                return

            # 3) Fetch URL object to read last_analysis_stats
            normalized = self.url if self.url.lower().startswith(("http://", "https://")) else f"http://{self.url}"
            url_id = url_to_vt_id(normalized)
            r = requests.get(f"{self.base}/urls/{url_id}", headers=self.headers, timeout=15)
            if r.status_code != 200:
                self.result.emit({"ok": False, "message": f"Fetch stats failed: {r.status_code} {r.text}"})
                return

            attrs = r.json().get("data", {}).get("attributes", {}) or {}
            stats = attrs.get("last_analysis_stats", {}) or {}

            # Derive a simple verdict
            mal = int(stats.get("malicious", 0))
            susp = int(stats.get("suspicious", 0))
            verdict = "BLOCK" if mal > 0 else "CAUTION" if susp > 0 else "SAFE"

            self.result.emit({"ok": True, "message": "Analysis completed.", "stats": stats, "verdict": verdict})
        except requests.RequestException as e:
            self.result.emit({"ok": False, "message": f"Network error: {e}"})
        except Exception as e:
            self.result.emit({"ok": False, "message": f"Unexpected error: {e}"})


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")
        self.resize(450, 450)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.setup_main_screen()
        self.setup_score_screen()

        self._worker = None

    def setup_main_screen(self):
        main_screen = QWidget()
        page = QVBoxLayout(main_screen)
        page.setContentsMargins(40, 40, 40, 40)

        main_screen.setStyleSheet("""
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

        title = QLabel("ENTER AN URL")
        tfont = QFont(); tfont.setPointSize(28); tfont.setBold(True)
        title.setFont(tfont); title.setAlignment(Qt.AlignHCenter)

        prompt = QLabel("Please enter a URL below and click OK to analyze with VirusTotal.")
        prompt.setAlignment(Qt.AlignHCenter)
        pfont = QFont(); pfont.setPointSize(12)
        prompt.setFont(pfont); prompt.setStyleSheet("color: #9aa5b1;")

        row = QHBoxLayout(); row.setSpacing(12)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("e.g., https://example.com or example.com/path")
        self.url_edit.setMinimumWidth(420)

        url_rx = QRegularExpression(
            r'^(?:https?://)?(?:localhost|(?:(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}))'
            r'(?::\d{1,5})?(?:/[^\s]*)?$'
        )
        url_rx.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
        self.url_edit.setValidator(QRegularExpressionValidator(url_rx, self))

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.on_ok)
        self.url_edit.returnPressed.connect(self.ok_btn.click)

        row.addWidget(self.url_edit, 1)
        row.addWidget(self.ok_btn)

        card_wrap.addWidget(title)
        card_wrap.addWidget(prompt)
        card_wrap.addLayout(row)

        page.addStretch(1)
        page.addWidget(card, 0, Qt.AlignHCenter)
        page.addStretch(1)

        self.stacked_widget.addWidget(main_screen)

    def setup_score_screen(self):
        score_screen = QWidget()
        score_screen.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0,y1:0, x2:0,y2:1,
                    stop:0 #0f172a, stop:1 #0b1220);
                color: #e5e7eb;
                font-size: 14px;
            }
            QPushButton {
                border: none; border-radius: 10px; padding: 10px 16px;
                background: #1d4ed8; color: white; font-weight: 600;
            }
            QPushButton:hover { background: #2563eb; }
            QPushButton:pressed { background: #1e40af; }
        """)
        layout = QVBoxLayout(score_screen)
        layout.setContentsMargins(40, 40, 40, 40)
        
        self.score_label = QLabel("Score: 0")
        font = QFont()
        font.setPointSize(36)
        font.setBold(True)
        self.score_label.setFont(font)
        self.score_label.setAlignment(Qt.AlignCenter)

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setFixedSize(100, 40)
        self.continue_btn.clicked.connect(self.on_continue)

        layout.addStretch(1)
        layout.addWidget(self.score_label, 0, Qt.AlignCenter)
        layout.addStretch(1)
        
        # Bottom right layout for the button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.continue_btn)
        layout.addLayout(bottom_layout)

        self.stacked_widget.addWidget(score_screen)


    def on_ok(self):
        api_key = os.environ.get("VIRUSTOTAL_API_KEY")
        url_text = self.url_edit.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Missing API key",
                                "Set VIRUSTOTAL_API_KEY in your environment or .env file.")
            return
        if not self.url_edit.hasAcceptableInput():
            QMessageBox.warning(self, "Invalid URL",
                                "Please enter a valid URL (domain or http/https URL).")
            return

        self.ok_btn.setEnabled(False)
        self.ok_btn.setText("Scanning...")

        self._worker = VTUrlScanThread(url_text, api_key, self)
        self._worker.result.connect(self.on_result)
        self._worker.start()

    def on_result(self, payload: dict):
        self.ok_btn.setEnabled(True)
        self.ok_btn.setText("OK")

        if not payload.get("ok"):
            QMessageBox.critical(self, "VirusTotal Error", payload.get("message", "Unknown error"))
            return

        stats = payload.get("stats", {}) or {}
        verdict = payload.get("verdict", "UNKNOWN")

        show_vt_box(self, verdict, stats)

        score = 0
        score += stats.get("malicious", 0) * 20
        score += stats.get("suspicious", 0) * 5
        score += stats.get("undetected", 0) * 0.2

        self.score_label.setText(f"Score: {score:.1f}")
        self.stacked_widget.setCurrentIndex(1)


    def on_continue(self):
        self.url_edit.clear()
        self.stacked_widget.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
