# --- Libraries ---
# Qt Libraries
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QStyle, QStyleOption
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QCursor, QPainter
from PySide6.QtWidgets import QProgressBar
import time

# Connection with service layer
from src.logic.vt_service import classify_kind, VTDeepScanThread
from src.logic.scanner_service import ScannerScanThread

# Connection with animations
from src.animations.AnimatedToggle import AnimatedToggle
from src.animations.CircularBar import CircularGraph

class Scanner_Window(QWidget):
    def __init__(self, userName, password, notify_callback=None):
        super().__init__()
        self.userName = userName 
        self.password = password
        self._notify_callback = notify_callback
        self._last_submitted_text = ""
        
        self.setWindowTitle(f"Scanner - User: {self.userName}")
        self.resize(1024, 682)
        
        # Timer (UI state)
        self._cooldown_left = 0
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._cooldown_tick)

        # Flag for switch between scans
        self.flagScanType = 0 # 0 Custom Scan, 1 Deep Scan
        self.stats = {}
        self.verdict = "UNKNOWN"
        self.signals = []
        
        # Create Main Layout
        self.setObjectName("SectionContent")
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)
        mainLayout.setSpacing(30)
        
        # Create frame
        card = QFrame()
        card.setObjectName("cardSettings")
        card_layout = QVBoxLayout(card) 
        mainLayout.addWidget(card)
 
        # Create Input Layout
        inputLayout = QVBoxLayout()
        inputLayout.setSpacing(10)

        title = QLabel("Enter a URL / DOMAIN / IP")
        title.setObjectName("TitleTables")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        inputLayout.addWidget(title)

        subtitle = QLabel("Type a full URL, domain or an IP and click OK.")
        subtitle.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        subtitle.setObjectName("Subtitle")
        inputLayout.addWidget(subtitle)

        scanTypeLayout = QHBoxLayout()
        scanTypeLayout.setSpacing(6)           
        scanTypeLayout.setContentsMargins(0, 0, 0, 0)

        scanTypeLabel = QLabel("Deep Scan:")
        scanTypeLabel.setObjectName("Subtitle")

        mainToggle = AnimatedToggle()
        mainToggle.setFixedSize(mainToggle.sizeHint())
        mainToggle.setCheckable(True)
        mainToggle.clicked.connect(self.deepScanOnOff)


        scanTypeLayout.addWidget(scanTypeLabel)
        scanTypeLayout.addWidget(mainToggle)
        scanTypeLayout.addStretch()            

        inputLayout.addLayout(scanTypeLayout)

        row = QHBoxLayout(); row.setSpacing(12)
        inputLayout.addLayout(row)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Example: https://example.com  |  example.com  |  8.8.8.8")
        self.input_edit.setMinimumWidth(420)
        self.input_edit.setFixedHeight(40)
        row.addWidget(self.input_edit, 1)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.setObjectName("ScannerButton")
        self.ok_btn.setMaximumHeight(40)
        self.ok_btn.clicked.connect(self.on_ok)
        self.input_edit.returnPressed.connect(self.ok_btn.click)
        row.addWidget(self.ok_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setObjectName("scanProgress")
        self._progress_accum = 0.0
        inputLayout.addWidget(self.progress)

        inputLayout.addSpacing(20) 
        inputLayout.addLayout(row)
        inputLayout.addWidget(self.progress)

        # Create Output Layout
        self.outputLayout = QHBoxLayout()
        self.minorScoreGraphLayout = QHBoxLayout()
        self.halfOutputLayout = QVBoxLayout()
        self.outputLayout.setSpacing(20)

        # Score graphs
        self.totalScoreGraph = CircularGraph()
        self.whoisScoreGraph = CircularGraph()
        self.dnsScoreGraph = CircularGraph()
        self.webScoreGraph = CircularGraph()
        
        self.totalScoreGraph.setTitle("Total Score")
        self.whoisScoreGraph.setTitle("Whois Score")
        self.dnsScoreGraph.setTitle("DNS Score")
        self.webScoreGraph.setTitle("Web Score")

        self.totalScoreGraph.setSize(250)
        self.dnsScoreGraph.setSize(150)
        self.webScoreGraph.setSize(150)
        self.whoisScoreGraph.setSize(150)


        self.outputLayout.addWidget(self.totalScoreGraph)
        self.minorScoreGraphLayout.addWidget(self.whoisScoreGraph)
        self.minorScoreGraphLayout.addWidget(self.dnsScoreGraph)
        self.minorScoreGraphLayout.addWidget(self.webScoreGraph)
        self.halfOutputLayout.addLayout(self.minorScoreGraphLayout)

        self.additionalDetailsButton = QPushButton()
        self.additionalDetailsButton.setObjectName("ScannerButton")
        self.additionalDetailsButton.setText("View Additional Details")
        self.additionalDetailsButton.hide()
        self.additionalDetailsButton.setCheckable(True)
        self.additionalDetailsButton.clicked.connect(self.showAdditionalDetailsDefaultScanner)
        self.halfOutputLayout.addWidget(self.additionalDetailsButton)    

        self.outputLayout.addLayout(self.halfOutputLayout)


        card_layout.addLayout(inputLayout)
        card_layout.addSpacing(40)
        card_layout.addLayout(self.outputLayout)
        card_layout.addStretch()

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(80)
        self._progress_timer.timeout.connect(self._advance_progress)
        self._worker = None

    def deepScanOnOff(self):
        self.flagScanType = not (self.flagScanType) 

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

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
        if self.flagScanType: 
            self.on_deep_scan()

        else: 
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
            self.additionalDetailsButton.show()

    def showAdditionalDetailsDefaultScanner(self):
        QTimer.singleShot(200, lambda: self.show_scan_box(self, self.verdict, self.stats, self.signals))

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

        self.stats = payload.get("stats", {}) or {}
        self.verdict = payload.get("verdict", "UNKNOWN")
        self.signals = payload.get("signals", [])
        scoreDNS = 0
        scoreWhois = 0
        scoreWeb = 0
        for section in self.signals:
            # Get if it is web, dns or whois
            section_identifier = section["name"].split("_")[0]
            risk_score = section.get("risk_score", 0)

            # Sum the risk scores
            match section_identifier:
                case "dns": 
                    scoreDNS = scoreDNS + risk_score
                case "domain" | "registrar" | "privacy" | "whois":
                    scoreWhois = scoreWhois + risk_score
                case "http" |"tls": 
                    scoreWeb = scoreWeb + risk_score
            
        # Connect the scores with the graphs
        risk_score = self.stats.get("risk_score", 0)
        self.totalScoreGraph.getScore(risk_score)
        self.dnsScoreGraph.getScore(scoreDNS)
        self.whoisScoreGraph.getScore(scoreWhois)
        self.webScoreGraph.getScore(scoreWeb)

        # # Small delay so user can see bar getting filled up (CAN REMOVE LATER MAYBE) @NicoVegaPortaluppi
        # QTimer.singleShot(200, lambda: self.show_scan_box(self, verdict, stats, signals))

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

        self.ok_btn.setEnabled(False)
        self.ok_btn.setText("Scanning...")

        self._deep_scan_worker = VTDeepScanThread(kind, target, self)
        self._deep_scan_worker.result.connect(self.on_deep_scan_result)
        self._deep_scan_worker.start()

    def on_deep_scan_result(self, payload: dict):
        self.ok_btn.setEnabled(True)
        self.ok_btn.setText("Ok")

        if not payload.get("ok"):
            QMessageBox.critical(
                self,
                "Deep Scan Error",
                payload.get("message", "Unknown error")
            )
            return

        stats = payload.get("stats", {}) or {}
        verdict = payload.get("verdict", "UNKNOWN")
        engine_results = payload.get("engine_results", {})
        self.start_cooldown(15) 

        QTimer.singleShot(
            200,
            lambda: self.show_vt_deep_scan_box(self, verdict, stats, engine_results)
        )

    def start_cooldown(self, seconds: int):
        self.cooldown_seconds = seconds
        self.ok_btn.setEnabled(False)

        self.cooldown_timer = QTimer(self)
        self.cooldown_timer.timeout.connect(self.update_cooldown)
        self.cooldown_timer.start(1000)

        self.update_cooldown()

    def update_cooldown(self):
        if self.flagScanType: 
            if self.cooldown_seconds > 0:
                self.ok_btn.setText(f"Cooldown: {self.cooldown_seconds}s")
                self.cooldown_seconds -= 1
            else:
                self.cooldown_timer.stop()
                self.ok_btn.setEnabled(True)
                self.ok_btn.setText("Ok")
        else: 
            self.ok_btn.setText("Ok")
            self.ok_btn.setEnabled(True)


    
    # --- Qt Presentation Functions ---
    def render_scan_html(self, verdict: str, stats: dict, signals: list = None) -> str:
        color = {
            "MALICIOUS": "#dc2626",
            "DANGEROUS": "#ef4444",
            "SUSPICIOUS": "#f97316",
            "CAUTION":   "#eab308",
            "NEUTRAL":   "#94a3b8",
            "SAFE":      "#22c55e",
            "SECURE":    "#059669",
            "BLOCK":     "#ef4444",
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

    def render_vt_deep_scan_html(self, verdict: str, stats: dict, engine_results: dict) -> str:
        color = {
            "MALICIOUS": "#dc2626",
            "DANGEROUS": "#ef4444",
            "SUSPICIOUS": "#f97316",
            "CAUTION":   "#eab308",
            "NEUTRAL":   "#94a3b8",
            "SAFE":      "#22c55e",
            "SECURE":    "#059669",
            "BLOCK":     "#ef4444",
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

    def show_vt_deep_scan_box(self, parent, verdict: str, stats: dict, engine_results: dict):
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
        box.setText(self.render_vt_deep_scan_html(verdict, stats, engine_results))
        box.setStandardButtons(QMessageBox.Ok)

        lbl = box.findChild(QLabel, "qt_msgbox_label")
        if lbl:
            lbl.setWordWrap(True)
            lbl.setMinimumSize(400, 250)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        box.exec()

    def show_scan_box(self, parent, verdict: str, stats: dict, signals: list = None):
        if verdict in ("MALICIOUS", "DANGEROUS", "SUSPICIOUS", "BLOCK"):
            icon = QMessageBox.Critical
        elif verdict in ("CAUTION", "NEUTRAL"):
            icon = QMessageBox.Warning
        else:
            icon = QMessageBox.Information
        box = QMessageBox(parent)
        box.setIcon(icon)
        box.setWindowTitle("Scan Result")
        box.setTextFormat(Qt.RichText)
        box.setText(self.render_scan_html(verdict, stats, signals))
        box.setStandardButtons(QMessageBox.Ok)

        lbl = box.findChild(QLabel, "qt_msgbox_label")
        if lbl:
            lbl.setWordWrap(True)
            lbl.setMinimumSize(500, 400)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        box.exec()