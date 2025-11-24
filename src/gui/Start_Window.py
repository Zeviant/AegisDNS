# Qt Libraries
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QTableView
from PySide6.QtGui import QPixmap, QIcon, QFont 
# Connection with other Windows
from src.gui.CreateAccount_Window import CreateAccount_Window
from src.SQL_Alchemy.database_manager import DatabaseManager
from src.gui.sidebar import SideBarMainWindow

# Server connection
from src.logic.backend_server import set_current_user, start_server_if_needed

class Start_Window(QWidget):
    def __init__(self):
        # --- Window SetUp ---
        super().__init__()
        self.setWindowTitle("Sign In")
        self.resize(1024, 682)
        self.centerOnScreen()

        # Fixed Box Size
        contentSquare = QWidget()
        contentSquare.setFixedSize(400, 360)  # 420, 360

        # --- User Icon ---
        userIcon_label = QLabel("")
        #userIcon_label.setIcon(QIcon("src\images\Login_icon\user_icon.png"))
        userIcon_label.setScaledContents(True)


        # --- Name and Password labels and line edits ---
        name_label = QLabel("Name")
        password_label = QLabel("Password")

        self.name_line_edit = QLineEdit()
        self.password_line_edit = QLineEdit()
        self.password_line_edit.setEchoMode(QLineEdit.Password) # Esto es para que salga como ****

        # --- Buttons ---
        login_button = QPushButton("Login")
        login_button.setDefault(True)
        signUp_button = QPushButton("Create Account")
        login_button.clicked.connect(self.login_account) # Connecting the actions to the login_account function
        signUp_button.clicked.connect(self.create_account) # Connecting the actions to the create_account function
       
       # --- Enter Keybind for logging in ---
        self.name_line_edit.returnPressed.connect(self.login_account)
        self.password_line_edit.returnPressed.connect(self.login_account)

        # --- Layouts ---
        # Layout for user icon
        userIcon_layout = QVBoxLayout()
        userIcon_layout.setSpacing(5)
        userIcon_layout.addWidget(userIcon_label)

        # Layout for name and password
        h_layout1 = QVBoxLayout()
        h_layout1.setSpacing(5)

        name_layout = QVBoxLayout()
        #name_layout.setSpacing(10)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_line_edit)
        
        pass_layout = QVBoxLayout()
        pass_layout.setSpacing(10)
        pass_layout.addWidget(password_label)
        pass_layout.addWidget(self.password_line_edit)

        h_layout1.addLayout(userIcon_layout)
        h_layout1.addLayout(name_layout)
        h_layout1.addLayout(pass_layout)

        # Layout for buttons
        h_layout2 = QVBoxLayout()
        h_layout2.setSpacing(10)
        h_layout2.addWidget(login_button)
        h_layout2.addWidget(signUp_button)

        # Layout for layouts xd
        full_layout = QVBoxLayout(contentSquare) # Attaching full_layout ot the widget contentSquare    
        full_layout.setSpacing(50)   
        full_layout.addLayout(h_layout1)
        full_layout.addLayout(h_layout2)
                
        # Layout to be attached to the main widget (self)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.addLayout(full_layout)
        self.root_layout.addWidget(contentSquare, alignment=QtCore.Qt.AlignCenter)  # Attaching the layout to the widget with self

    def create_account(self):
        self.create_window = CreateAccount_Window()
        self.create_window.show()
        

    def login_account(self):
        # Getting username and password
        username = self.name_line_edit.text()
        passwordH = self.password_line_edit.text()

        # Check if any field is empty
        if(self.name_line_edit.text() == "" or self.password_line_edit.text() == ""): 
            fieldsEmpty_box = QMessageBox()
            fieldsEmpty_box.setWindowTitle("ERROR")
            fieldsEmpty_box.setIcon(QMessageBox.Warning)
            fieldsEmpty_box.setText("Some fields are empty!")
            fieldsEmpty_box.exec()
        
        else: 
            
            if DatabaseManager.authenticate_user(username, passwordH): 
                # Load Sheet Style
                with open("src/gui/Style_Sheet/sidebar_Style.qss") as f: 
                    style_str = f.read()

                # Username and password are passed to the mainwindow
                self.MainMenu = SideBarMainWindow(username, passwordH)
                self.MainMenu.setStyleSheet(style_str)
                self.MainMenu.show()

                # Start local extension server
                start_server_if_needed()
                set_current_user(username)
                
                # Close current window
                self.close()
            
            else:
                login_fail_box = QMessageBox()
                login_fail_box.setWindowTitle("ERROR")
                login_fail_box.setIcon(QMessageBox.Warning)
                login_fail_box.setText("Username or password wrong")
                login_fail_box.exec()
            
    
    def centerOnScreen (self):
        screen = self.screen()  # get the QScreen the window is on
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        x = (geometry.width() - self.width()) // 2
        y = (geometry.height() - self.height()) // 2
        self.move(x, y) 

# Not necessary since it is executed from main
# if __name__ == "__main__":
#     app = QApplication([])
#     window = Start_Window()
#     window.show()  
#     app.exec()