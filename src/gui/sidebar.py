from PySide6.QtWidgets import QMainWindow, QLabel, QListWidgetItem, QWidget, QGridLayout, QSystemTrayIcon
from PySide6.QtCore import Qt, QSize, QTimer, QThread
from PySide6.QtGui import QPixmap, QIcon, QFont 
from src.gui.uiFiles.sidebar_ui import Ui_MainWindow
from src.logic.vt_service import get_sorted_history

# Import pages 
from src.gui.history_window import History_Window
from src.gui.main_window import Main_Window
from src.gui.Scanner_Window import Scanner_Window
from src.gui.log_window import Log_Window 
from src.gui.WhiteBlackList_Window import WhiteBlackList_Window
from src.gui.settings_window import Settings_Window
from src.gui.SnifferContainer_Window import SnifferContainer_Window
from src.gui.packet_sniffer_widget import PacketSnifferWidget
import os
import json
import time

# Start ps
from sniffer_test.sniffer_worker import SnifferWorker
from sniffer_test.aggregator import RollingAggregator
from threading import Thread
from sniffer_test.packet_sniffer import start_sniffing
# end ps

from src.gui.packet_sniffer_widget import PacketSnifferWidget
# Define MainWindow Class
class SideBarMainWindow(QMainWindow):
    def __init__(self,  user_name: str, password: str):
        # Window SetUp
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.username = user_name
        self.password = password
        self.setWindowTitle("Capstone Application")
        self.setWindowIcon(QIcon("src/images/SideBar_icons/logo.png"))

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(QIcon("src\\images\\SideBar_icons\\logo.png"), self)
        self.tray_icon.setToolTip("DNS Monitor")
        self.tray_icon.show()

        # Settings file path for mute notifications
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.SETTINGS_FILE = os.path.join(BASE_DIR, "..", "VT_Cache", "settings.json")

        # Initialize UI elements 
        self.title_label = self.ui.title_label
        self.title_label.setText("DNS")
        
        self.title_icon = self.ui.title_icon
        self.title_icon.setText("")
        self.title_icon.setPixmap(QPixmap("src\images\SideBar_icons\logo.png"))
        self.title_icon.setScaledContents(True)

        self.sideMenu = self.ui.listWidget
        self.sideMenu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sideMenuIcon = self.ui.listWidget_icon
        self.sideMenuIcon.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sideMenuIcon.hide()

        self.sideMenuButton = self.ui.pushButton
        self.sideMenuButton.setObjectName("SideMenuButton")
        self.sideMenuButton.setText("")
        self.sideMenuButton.setIcon(QIcon("src\images\SideBar_icons\menu-bar.png"))
        self.sideMenuButton.setIconSize(QSize(30, 30))
        self.sideMenuButton.setCheckable(True)
        self.sideMenuButton.setChecked(False)
        self.mainContent = self.ui.stackedWidget

        # Start ps
        self.aggregator = RollingAggregator(window_seconds=30)
        self.sniffer_thread_native = Thread(
            target=start_sniffing,
            args=(self.aggregator,),
            daemon=True
        )
        self.sniffer_thread_native.start()

        self.sniffer_thread = QThread()
        self.sniffer_worker = SnifferWorker(self.aggregator)

        self.sniffer_worker.moveToThread(self.sniffer_thread)

        self.sniffer_thread.started.connect(self.sniffer_worker.start)
        self.sniffer_worker.data_ready.connect(self.handle_sniffer_data)

        self.sniffer_thread.start()

        # end ps

        # List of menu items
        self.menuList = [
            {"name": "Analyze Address", "icon": "src\\images\\SideBar_icons\\analyze_icon.png", "widget": Scanner_Window(self.username, self.password, notify_callback=self.show_verdict_notification),}, 
            {"name": "History File", "icon": "src\\images\\SideBar_icons\\history_icon.png", "widget": History_Window(self.username, sidebar_reference=self)},
            {"name": "Navigation Logs", "icon": "src\\images\\SideBar_icons\\navigation_white_icon.png", "widget": Log_Window(self.username, sidebar_reference=self)},
            {"name": "Packets", "icon": "src\\images\\SideBar_icons\\packets_icon.png", "widget": WhiteBlackList_Window(self.username)},
            {"name": "White/Black List", "icon": "src\\images\\SideBar_icons\\list_icon.png", "widget": SnifferContainer_Window()},
            {"name": "Settings", "icon": "src\\images\\SideBar_icons\\settings_icon.png", "widget": Settings_Window(self.username, sidebar_reference=self)},
        ]

        # Call the functions
        self.listWidget()
        self.signalSlot()
        self.stackWidget()

        self._last_notified_ts: str | None = None
        self._notify_timer = QTimer(self)
        self._notify_timer.setInterval(5000)  
        self._notify_timer.timeout.connect(self._check_new_scans_for_notifications)
        self._notify_timer.start()

        self._packet_log_timer = QTimer(self)
        self._packet_log_timer.setInterval(10_000)
        self._packet_log_timer.timeout.connect(self._log_packet_counts)
        self._packet_log_timer.start()

    def whichProtocol(self, snapshot):
        if not snapshot:
            return

        latest = snapshot[-1]

        tcp = latest.get("tcp_packets", 0)
        udp = latest.get("udp_packets", 0)
        dns = latest.get("dns_packets", 0)

        if tcp > udp:
            dominant = "TCP"
            subservient = "UDP"
        elif udp > tcp:
            dominant = "UDP"
            subservient = "TCP"
        else:
            dominant = "Mixed"

        extras = []
        if dns > 0:
            extras.append("DNS")
        if udp > 0 and dominant == "TCP":
            extras.append("background UDP")
        if tcp > 0 and dominant == "UDP":
            extras.append("background TCP")

        if extras:
            print(f"{dominant} ({', '.join(extras)})")
        else:
            print(dominant)
        
        
    def _log_packet_counts(self):
        snapshot = self.aggregator.get_snapshot()
        if not snapshot:
            print("[Sniffer] last 10s: no data")
            return

        now = int(time.time())
        cutoff = now - 10
        tcp = udp = 0
        unique_senders = set()
        for bucket in snapshot:
            if bucket.get("timestamp", 0) >= cutoff:
                tcp += bucket.get("tcp_packets", 0)
                udp += bucket.get("udp_packets", 0)
                srcs = bucket.get("src_ips", set())
                unique_senders.update(srcs)

        total = tcp + udp
        unique_count = len(unique_senders)
        print(f"[Sniffer] last 10s: TCP={tcp} UDP={udp} total={total} unique_senders={unique_count}")

        # Update the protocol animation counters with real sniffer data
        if tcp > udp:
            dominant = "TCP"
            subservient = "UDP"
        elif udp > tcp:
            dominant = "UDP"
            subservient = "TCP"
        else:
            dominant = "Mixed"
            subservient = "TCP"
            
        if hasattr(self, "PacketsWindowPage"):
            self.PacketsWindowPage.update_packet_counts(tcp, udp)
            if (dominant == "TCP"):
                self.PacketsWindowPage.sent_dominant_animation(dominant, tcp, subservient, udp)
            if (dominant == "UDP"):
                self.PacketsWindowPage.sent_dominant_animation(dominant, udp, subservient, tcp)
            if (dominant == "Mixed"):
                self.PacketsWindowPage.sent_dominant_animation(dominant, tcp, subservient, udp)

        self.whichProtocol(snapshot)

    def closeEvent(self, event):
        if hasattr(self, "sniffer_worker"):
            self.sniffer_worker.stop()

        if hasattr(self, "sniffer_thread"):
            self.sniffer_thread.quit()
            self.sniffer_thread.wait()

        event.accept()

    def handle_sniffer_data(self, snapshot):
        if not snapshot:
            return

        if hasattr(self, "PacketsWindowPage"):
            self.PacketsWindowPage.update_sniffer_data(snapshot)


    def _check_new_scans_for_notifications(self):
        entries = get_sorted_history(self.username)

        if not entries:
            return

        # Avoid notifying old entries
        if self._last_notified_ts is None:
            self._last_notified_ts = entries[0].get("ts", "")
            return

        newest_ts = entries[0].get("ts", "")
        if not newest_ts or newest_ts == self._last_notified_ts:
            return

        # Collect entries newer than last_notified_ts
        new_entries = []
        for entry in entries:
            ts = entry.get("ts", "")
            if ts == self._last_notified_ts:
                break
            new_entries.append(entry)

        # Update ts even if no entries found
        if not new_entries:
            self._last_notified_ts = newest_ts
            return

        # Notify from oldest to newest
        for entry in reversed(new_entries):
            verdict = entry.get("verdict", "UNKNOWN").upper()
            target = entry.get("target", "")
            self.show_verdict_notification(verdict, target)

        # Update ts to newest entry time
        self._last_notified_ts = newest_ts

    def is_notifications_muted(self) -> bool:
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    return settings.get("mute_notifications", False)
        except Exception:
            pass
        return False

    def show_verdict_notification(self, verdict: str, target: str = ""):
        if self.is_notifications_muted():
            return  # Don't show notification if muted

        if verdict in ("MALICIOUS", "DANGEROUS", "SUSPICIOUS", "BLOCK"):
            icon = QSystemTrayIcon.Critical
        elif verdict in ("CAUTION", "NEUTRAL"):
            icon = QSystemTrayIcon.Warning
        else:
            icon = QSystemTrayIcon.Information

        title = "Scan complete"
        message = f"Verdict: {verdict}"
        if target:
            message = f"{message} for {target}"

        # The last parameter is duration in ms
        self.tray_icon.showMessage(title, message, icon, 5000)
    
    def signalSlot(self): 
        # If sideMenuButton is pressed
        self.sideMenuButton.toggled["bool"].connect(self.sideMenu.setHidden)
        self.sideMenuButton.toggled["bool"].connect(self.title_icon.setHidden)
        self.sideMenuButton.toggled["bool"].connect(self.title_label.setHidden)
        self.sideMenuButton.toggled["bool"].connect(self.sideMenuIcon.setVisible)

        # Switch between menu items
        self.sideMenu.currentRowChanged["int"].connect(self.mainContent.setCurrentIndex)
        self.sideMenuIcon.currentRowChanged["int"].connect(self.mainContent.setCurrentIndex)
        self.sideMenu.currentRowChanged["int"].connect(self.sideMenuIcon.setCurrentRow)
        self.sideMenuIcon.currentRowChanged["int"].connect(self.sideMenu.setCurrentRow)

        self.sideMenuButton.toggled.connect(self.buttonIconChange)

    # This is to change the buttons Icon, but idk, maybe we just keep the three lines
    def buttonIconChange(self, status): 
        if status: 
            self.sideMenuButton.setIcon(QIcon("src\images\SideBar_icons\menu-bar.png"))
        else: 
            self.sideMenuButton.setIcon(QIcon("src\images\SideBar_icons\menu-bar.png"))

    def listWidget(self): 
        self.sideMenu.clear()
        self.sideMenuIcon.clear()

        for menu in self.menuList: 
            item = QListWidgetItem()
            item.setIcon(QIcon(menu.get("icon")))
            item.setSizeHint(QSize(40, 40))
            self.sideMenuIcon.addItem(item)
            self.sideMenuIcon.setCurrentRow(0)

            itemNew = QListWidgetItem()
            itemNew.setIcon(QIcon(menu.get("icon")))
            itemNew.setText(menu.get("name"))
            self.sideMenu.addItem(itemNew)
            self.sideMenu.setCurrentRow(0)

    def stackWidget(self): 
        widgetList = self.mainContent.findChildren(QWidget)
        for widget in widgetList: 
            self.mainContent.removeWidget(widget)

        # Create instances of each page
        self.StartWindowPage = Scanner_Window(self.username, self.password, notify_callback=self.show_verdict_notification)
        self.MainWindowPage = History_Window(self.username)
        self.LogWindowPage = Log_Window(self.username, sidebar_reference=self)
        self.PacketsWindowPage = SnifferContainer_Window()
        self.WhiteBlackListPage = WhiteBlackList_Window(self.username) 
        self.SettingsPage = Settings_Window(self.username, sidebar_reference=self) 
         

        # Add them to stacked widget
        self.mainContent.addWidget(self.StartWindowPage)
        self.mainContent.addWidget(self.MainWindowPage)
        self.mainContent.addWidget(self.LogWindowPage)
        self.mainContent.addWidget(self.PacketsWindowPage)
        self.mainContent.addWidget(self.WhiteBlackListPage)
        self.mainContent.addWidget(self.SettingsPage)

        for menu in self.menuList: 
            text = menu.get("name")
            layout = QGridLayout()
            label = QLabel(text=text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = QFont()
            font.setPixelSize(20)
            label.setFont(font)
            layout.addWidget(label)
            new_page = QWidget()
            new_page.setLayout(layout)

        # Add each menu widget to the stacked widget in order
        for menu in self.menuList:
            self.mainContent.addWidget(menu["widget"])
