# --- Libraries ---
# Qt Libraries
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QCursor
from PySide6.QtWidgets import QProgressBar
import time

# Connection with service layer
from src.logic.vt_service import classify_kind, VTDeepScanThread
from src.logic.scanner_service import ScannerScanThread

# --- Qt Presentation Functions ---
def render_scan_html(verdict: str, stats: dict, signals: list = None) -> str:
    color = {
        "MALICIOUS": "#dc2626", "DANGEROUS": "#ef4444", "SUSPICIOUS": "#f97316",
        "CAUTION": "#eab308", "NEUTRAL": "#94a3b8",
        "SAFE": "#22c55e", "SECURE": "#059669",
        "BLOCK": "#ef4444",
    }.get(verdict, "#94a3b8")
    risk_score = stats.get("risk_score", 0)
    
    signals_html = ""
    if signals:
        signals_html = "<div style='margin-top:12px;'><div style='color:#9aa5b1; margin-bottom:8px;'>Signals Detected:</div><ul style='margin:0; padding-left:20px; color:#e5e7eb;'>"
        for signal in signals:
            signal_name = signal.get("name", "Unknown")
            signal_score = signal.get("risk_score", 0)
            signal_reason = signal.get("reason", "")
            if signal_reason:
                signals_html += f"<li style='margin-bottom:4px;'>{signal_name}: {signal_score} ({signal_reason})</li>"
            else:
                signals_html += f"<li style='margin-bottom:4px;'>{signal_name}: {signal_score}</li>"
        signals_html += "</ul></div>"
    
    return f"""
      <div style="font-family:'Segoe UI',Arial; font-size:14px; color:#e5e7eb;">
        <h2 style="margin:0 0 12px; font-size:22px; color:{color};">Verdict: {verdict}</h2>
        <table style="border-collapse:collapse; margin-top:6px;">
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Risk Score</td>
              <td style="padding:4px 12px; font-weight:600;">{risk_score}</td></tr>
        </table>
        {signals_html}
        <p style="margin-top:12px; color:#9aa5b1;">Source: Custom Scanner</p>
      </div>
    """

def render_vt_deep_scan_html(verdict: str, stats: dict, engine_results: dict) -> str:
    color = {
        "MALICIOUS": "#dc2626", "DANGEROUS": "#ef4444", "SUSPICIOUS": "#f97316",
        "CAUTION": "#eab308", "NEUTRAL": "#94a3b8",
        "SAFE": "#22c55e", "SECURE": "#059669",
        "BLOCK": "#ef4444",
    }.get(verdict, "#94a3b8")
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    harmless = stats.get("harmless", 0)
    undetected = stats.get("undetected", 0)
    
    return f"""
      <div style="font-family:'Segoe UI',Arial; font-size:14px; color:#e5e7eb;">
        <h2 style="margin:0 0 12px; font-size:22px; color:{color};">Verdict: {verdict}</h2>
        <table style="border-collapse:collapse; margin-top:6px;">
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Malicious</td>
              <td style="padding:4px 12px; font-weight:600; color:#ef4444;">{malicious}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Suspicious</td>
              <td style="padding:4px 12px; font-weight:600; color:#f59e0b;">{suspicious}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Harmless</td>
              <td style="padding:4px 12px; font-weight:600; color:#10b981;">{harmless}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Undetected</td>
              <td style="padding:4px 12px; font-weight:600;">{undetected}</td></tr>
        </table>
        <p style="margin-top:12px; color:#9aa5b1;">Source: VirusTotal Deep Scan</p>
      </div>
    """

def show_vt_deep_scan_box(parent, verdict: str, stats: dict, engine_results: dict):
    if verdict in ("MALICIOUS", "DANGEROUS", "SUSPICIOUS", "BLOCK"):
        icon = QMessageBox.Critical
    elif verdict in ("CAUTION", "NEUTRAL"):
        icon = QMessageBox.Warning
    else:
        icon = QMessageBox.Information
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle("Deep Scan Result")
    box.setTextFormat(Qt.RichText)
    box.setText(render_vt_deep_scan_html(verdict, stats, engine_results))
    box.setStandardButtons(QMessageBox.Ok)

    lbl = box.findChild(QLabel, "qt_msgbox_label")
    if lbl:
        lbl.setWordWrap(True)
        lbl.setMinimumSize(400, 250)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

    box.exec()

def show_scan_box(parent, verdict: str, stats: dict, signals: list = None, silent: bool = False):
    if verdict in ("MALICIOUS", "DANGEROUS", "SUSPICIOUS", "BLOCK"):
        icon = QMessageBox.Critical
    elif verdict in ("CAUTION", "NEUTRAL"):
        icon = QMessageBox.Warning
    else:
        icon = QMessageBox.Information

    effective_icon = QMessageBox.NoIcon if silent else icon

    box = QMessageBox(parent)
    box.setIcon(effective_icon)
    box.setWindowTitle("Scan Result")
    box.setTextFormat(Qt.RichText)
    box.setText(render_scan_html(verdict, stats, signals))
    box.setStandardButtons(QMessageBox.Ok)

    lbl = box.findChild(QLabel, "qt_msgbox_label")
    if lbl:
        lbl.setWordWrap(True)
        lbl.setMinimumSize(500, 400)
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
        central.setObjectName("SectionContent")
        self.setCentralWidget(central)
        page = QVBoxLayout(central)
        page.setContentsMargins(40, -100, 40, 40)
        page.setSpacing(0)

        card = QFrame()
        card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(blurRadius=40, xOffset=0, yOffset=12)
        shadow.setColor(Qt.black)
        card.setGraphicsEffect(shadow)

        card_wrap = QVBoxLayout(card)
        card_wrap.setContentsMargins(48, 48, 48, 48)
        card_wrap.setSpacing(24)

        title = QLabel("ENTER A URL / DOMAIN / IP")
        title.setObjectName("TitleTables")
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
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.clicked.connect(self.on_ok)
        self.input_edit.returnPressed.connect(self.ok_btn.click)

        row.addWidget(self.input_edit, 1)
        row.addWidget(self.ok_btn)
        
        card_wrap.addWidget(title)
        card_wrap.addWidget(prompt)
        card_wrap.addLayout(row)
        card_wrap.addWidget(self.progress)

        # Logo (Aegis DNS)
        # logo = QLabel()
        # logo.setStyleSheet("background: transparent;")
        # logo_pix = QPixmap("src/images/Other_icons/AegisDNS_Logo.png")
        # if not logo_pix.isNull():
        #     logo.setPixmap(logo_pix.scaledToWidth(375, Qt.SmoothTransformation))
        # logo.setAlignment(Qt.AlignHCenter)

        # page.addWidget(logo, 0, Qt.AlignHCenter)
        page.addWidget(card, 0, Qt.AlignHCenter)
        page.addStretch(2)
        
        # Deep Scan section
        # deep_scan_layout = QHBoxLayout()
        # deep_scan_layout.setSpacing(8)
        # deep_scan_layout.setContentsMargins(0, 0, 0, 0)
        
        # self.deep_scan_btn = QPushButton("DEEP SCAN")
        # # self.deep_scan_btn.setObjectName("deepScanButton")
        # self.deep_scan_btn.setMinimumHeight(40)
        # self.deep_scan_btn.setMinimumWidth(120)
        # vt_logo = QLabel()
        # vt_logo_pix = QPixmap("src/images/Other_icons/VirusTotal_logo.svg.png")
        # if not vt_logo_pix.isNull():
        #     vt_logo.setPixmap(vt_logo_pix.scaledToHeight(24, Qt.SmoothTransformation))
        # vt_logo.setAlignment(Qt.AlignCenter)
        
        # # Info icon with tooltip
        # info_icon = QLabel("?")
        # info_icon.setObjectName("infoIcon")
        # info_icon.setAlignment(Qt.AlignCenter)
        # info_icon.setFixedSize(20, 20)
        # info_font = QFont()
        # info_font.setPointSize(10)
        # info_font.setBold(True)
        # info_icon.setFont(info_font)
        # info_icon.setCursor(QCursor(Qt.PointingHandCursor))
        
        # tooltip_text = (
        #     "Performs a scan using VirusTotal's API. <br>"
        #     "VirusTotal uses over 90 different antivirus engines and is far more extensive than the basic scan."
        # )
        # info_icon.setToolTip(tooltip_text)
        # info_icon.setEnabled(True)
        # info_icon.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        
        # deep_scan_layout.addWidget(self.deep_scan_btn)
        # deep_scan_layout.addWidget(vt_logo)
        # deep_scan_layout.addWidget(info_icon)
        # deep_scan_layout.addStretch()
        
        # self.deep_scan_btn.clicked.connect(self.on_deep_scan)
        
        # deep_scan_widget = QWidget()
        # deep_scan_widget.setLayout(deep_scan_layout)
        # deep_scan_widget.setStyleSheet("background: transparent;")
        # page.addWidget(deep_scan_widget, 0, Qt.AlignLeft | Qt.AlignBottom)

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(80)
        self._progress_timer.timeout.connect(self._advance_progress)
        self._worker = None
        self._deep_scan_worker = None
        self._deep_scan_cooldown_left = 0
        self._deep_scan_cooldown_timer = QTimer(self)
        self._deep_scan_cooldown_timer.setInterval(1000)
        self._deep_scan_cooldown_timer.timeout.connect(self._deep_scan_cooldown_tick)  

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
        self._worker = ScannerScanThread(kind, target, self.userName, self)
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
            # Error message from the scanner service
            QMessageBox.critical(self, "Scan Error", payload.get("message", "Unknown error"))
            return

        stats = payload.get("stats", {}) or {}
        verdict = payload.get("verdict", "UNKNOWN")
        signals = payload.get("signals", [])

        # Small delay so user can see bar getting filled up (CAN REMOVE LATER MAYBE) @NicoVegaPortaluppi
        QTimer.singleShot(200, lambda: show_scan_box(self, verdict, stats, signals))

    def _deep_scan_cooldown_tick(self):
        self._deep_scan_cooldown_left -= 1
        if self._deep_scan_cooldown_left <= 0:
            self._deep_scan_cooldown_timer.stop()
            self.deep_scan_btn.setEnabled(True)
            self.deep_scan_btn.setText("DEEP SCAN")
        else:
            self.deep_scan_btn.setText(f"Cooldown: {self._deep_scan_cooldown_left}s")

    def start_deep_scan_cooldown(self, seconds: int):
        self._deep_scan_cooldown_left = max(1, int(seconds))
        self.deep_scan_btn.setEnabled(False)
        self.deep_scan_btn.setText(f"Cooldown: {self._deep_scan_cooldown_left}s")
        self._deep_scan_cooldown_timer.start()

    def on_deep_scan(self):
        raw = self.input_edit.text().strip()

        if not raw:
            QMessageBox.warning(self, "Empty input", "Please enter a URL, domain, or IP.")
            return

        try:
            kind, target = classify_kind(raw)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return

        self.deep_scan_btn.setEnabled(False)
        self.deep_scan_btn.setText("Scanning...")

        self._deep_scan_worker = VTDeepScanThread(kind, target, self)
        self._deep_scan_worker.tick.connect(self.on_deep_scan_cooldown_tick)
        self._deep_scan_worker.result.connect(self.on_deep_scan_result)
        self._deep_scan_worker.start()

    def on_deep_scan_cooldown_tick(self, secs_left: int):
        self.deep_scan_btn.setText(f"Cooldown: {secs_left}s" if secs_left > 0 else "Scanning...")

    def on_deep_scan_result(self, payload: dict):
        self.deep_scan_btn.setEnabled(True)
        self.deep_scan_btn.setText("DEEP SCAN")

        if not payload.get("ok"):
            QMessageBox.critical(self, "Deep Scan Error", payload.get("message", "Unknown error"))
            return

        stats = payload.get("stats", {}) or {}
        verdict = payload.get("verdict", "UNKNOWN")
        engine_results = payload.get("engine_results", {})

        QTimer.singleShot(200, lambda: show_vt_deep_scan_box(self, verdict, stats, engine_results))
