from PySide6.QtWidgets import QMainWindow, QLabel, QListWidgetItem, QWidget, QGridLayout
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QFont 
from src.gui.uiFiles.sidebar_ui import Ui_MainWindow

# Import pages 
from src.gui.history_window import History_Window
from src.gui.main_window import Main_Window 

# Define MainWindow Class
class SideBarMainWindow(QMainWindow):
    def __init__(self,  user_name: str, password: str):
        # Window SetUp
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.username = user_name
        self.password = password

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

        # List of menu items
        self.menuList = [
            {"name": "Analyze Address", "icon": "src\\images\\SideBar_icons\\analyze_icon.png", "widget": Main_Window(self.username, self.password)}, 
            {"name": "History File", "icon": "src\images\SideBar_icons\history_icon.png", "widget": History_Window(self.username)},
            {"name": "Packets", "icon": "src\images\SideBar_icons\packets_icon.png", "widget": QWidget()},
            {"name": "White/Black List", "icon": "src\images\SideBar_icons\list_icon.png", "widget": QWidget()},
            {"name": "Settings", "icon": "src\images\SideBar_icons\settings_icon.png", "widget": QWidget()},
        ]

        # Call the functions
        self.listWidget()
        self.signalSlot()
        self.stackWidget()
    
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
        self.StartWindowPage = Main_Window(self.username, self.password)
        self.MainWindowPage = History_Window(self.username) 
        self.PacketsWindowPage = QWidget()
        self.WhiteBlackListPage = QWidget() 
        self.SettingsPage = QWidget() 
         

        # Add them to stacked widget
        self.mainContent.addWidget(self.StartWindowPage)
        self.mainContent.addWidget(self.MainWindowPage)
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
            self.mainContent.addWidget(menu["widget"])



