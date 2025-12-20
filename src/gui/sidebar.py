from PySide6.QtWidgets import QMainWindow, QLabel, QListWidgetItem, QWidget, QGridLayout, QSystemTrayIcon
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QIcon, QFont 
from src.gui.uiFiles.sidebar_ui import Ui_MainWindow
from src.logic.vt_service import get_sorted_history

# Import pages 
from src.gui.history_window import History_Window
from src.gui.main_window import Main_Window
from src.gui.log_window import Log_Window 
from src.gui.WhiteBlackList_Window import WhiteBlackList_Window
from PySide6.QtCore import QThread

# Start ps
from sniffer_test.sniffer_worker import SnifferWorker
from sniffer_test.aggregator import RollingAggregator
from threading import Thread
from sniffer_test.packet_sniffer import start_sniffing
# end ps

# from Capstone.src.gui.packet_sniffer_widget import LiveChart

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
            {
                "name": "Analyze Address",
                "icon": "src\\images\\SideBar_icons\\analyze_icon.png",
                "widget": Main_Window(self.username, self.password, notify_callback=self.show_verdict_notification),
            }, 
            {"name": "History File", "icon": "src\images\SideBar_icons\history_icon.png", "widget": History_Window(self.username)},
            {"name": "Navigation Logs", "icon": "src\images\SideBar_icons\history_icon.png", "widget": Log_Window(self.username, sidebar_reference=self)},
            {"name": "Packets", "icon": "src\images\SideBar_icons\packets_icon.png", "widget": WhiteBlackList_Window(self.username)},
            {"name": "White/Black List", "icon": "src\images\SideBar_icons\list_icon.png", "widget": PacketSnifferWidget()},
            {"name": "Settings", "icon": "src\images\SideBar_icons\settings_icon.png", "widget": QWidget()},
        ]

        # Call the functions
        self.listWidget()
        self.signalSlot()
        self.stackWidget()

        # Periodically poll history to show notifications for any scans
        self._last_notified_ts: str | None = None
        self._notify_timer = QTimer(self)
        self._notify_timer.setInterval(5000)  # 5 seconds
        self._notify_timer.timeout.connect(self._check_new_scans_for_notifications)
        self._notify_timer.start()


    def closeEvent(self, event):
        # Stop sniffer worker
        if hasattr(self, "sniffer_worker"):
            self.sniffer_worker.stop()

        if hasattr(self, "sniffer_thread"):
            self.sniffer_thread.quit()
            self.sniffer_thread.wait()

        event.accept()

    def handle_sniffer_data(self, snapshot):
        if not snapshot:
            return

        # Forward data to PacketSnifferWidget
        if hasattr(self, "PacketsWindowPage"):
            self.PacketsWindowPage.update_data(snapshot)


    def _check_new_scans_for_notifications(self):
        """
        Polls the VT history log and shows notifications for new entries.
        This makes it so that scans triggered outside the GUI (e.g. browser extension) can create a notification.
        (Could maybe make a better implementation later, but trying to create a notification
        from backend_server.py was causing issues)
        """
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

    def show_verdict_notification(self, verdict: str, target: str = ""):
        if verdict == "BLOCK":
            icon = QSystemTrayIcon.Critical
        elif verdict == "CAUTION":
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
        self.StartWindowPage = Main_Window(self.username, self.password, notify_callback=self.show_verdict_notification)
        self.MainWindowPage = History_Window(self.username)
        self.LogWindowPage = Log_Window(self.username, sidebar_reference=self)
        self.PacketsWindowPage = PacketSnifferWidget()
        self.WhiteBlackListPage = WhiteBlackList_Window(self.username) 
        self.SettingsPage = QWidget() 
         

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
