# Qt Libraries
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel
from sqlalchemy import Column, Integer, String, ForeignKey, Sequence, CHAR, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Connection to other modules
from src.SQL_Alchemy.database import User, session
class CreateAccount_Window(QWidget): 
    # Window SetUp
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create Account Window")
        self.setGeometry(600, 500, 600, 500)
        self.centerOnScreen()

        # Fixed Box Size
        contentSquare = QWidget()
        contentSquare.setFixedSize(300, 300) 

        # First name and Last name labels and line edits
        firstName_label = QLabel("First Name")
        lastName_label = QLabel("Last Name")

        self.firstName_line_edit = QLineEdit()
        self.lastName_line_edit = QLineEdit()

        # Name and Password labels and line edits 
        userName_label = QLabel("User Name")
        password_label = QLabel("Password")
        confirmPass_label = QLabel("Confirm Password")

        self.userName_line_edit = QLineEdit()
        self.password_line_edit = QLineEdit()
        self.confirmPass_line_edit = QLineEdit()
        

        # --- Buttons ---
        ok_button = QPushButton("Ok")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.create_account) # Connecting the actions to the create_account function
        cancel_button.clicked.connect(self.close_window) # Connecting the actions to the close_account function

        # --- Layouts ---
        # Layout for name and password
        h_layout1 = QVBoxLayout()

        fullName_layout = QVBoxLayout()
        fullName_layout.addWidget(firstName_label)
        fullName_layout.addWidget(self.firstName_line_edit)
        fullName_layout.addWidget(lastName_label)
        fullName_layout.addWidget(self.lastName_line_edit)

        userName_layout = QVBoxLayout()
        userName_layout.addWidget(userName_label)
        userName_layout.addWidget(self.userName_line_edit)
        
        pass_layout = QVBoxLayout()
        pass_layout.addWidget(password_label)
        pass_layout.addWidget(self.password_line_edit)
        pass_layout.addWidget(confirmPass_label)
        pass_layout.addWidget(self.confirmPass_line_edit)

        h_layout1.addLayout(fullName_layout)
        h_layout1.addLayout(userName_layout)
        h_layout1.addLayout(pass_layout)

        # Layout for buttons
        h_layout2 = QHBoxLayout()
        h_layout2.setSpacing(10)
        h_layout2.addWidget(ok_button)
        h_layout2.addWidget(cancel_button)

        full_layout = QVBoxLayout()
        full_layout.addLayout(h_layout1)
        full_layout.addLayout(h_layout2)
        contentSquare.setLayout(full_layout)

        # --- Root layout ---
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(contentSquare, alignment=QtCore.Qt.AlignCenter)  # Attaching the layout to the widget with self

    def create_account(self): 
        firstName = self.firstName_line_edit.text()
        lastName = self.lastName_line_edit.text()
        userName = self.userName_line_edit.text()
        password = self.password_line_edit.text()
        cpassword = self.confirmPass_line_edit.text()

        # In case passwords does not match
        if (password != cpassword): 
                passwordMissmatch_box = QMessageBox()
                passwordMissmatch_box.setIcon(QMessageBox.Warning)
                passwordMissmatch_box.setText("Passwords must match!")
                passwordMissmatch_box.exec()
        
        self.addNewUserToDatabase(userName, password)

    def addNewUserToDatabase(self, user, password): 
        db = QSqlDatabase.addDatabase("QSQLITE")
        db.setDatabaseName("C:/Users/Nico/Desktop/Capstone/DNS Project/Capstone/src/SQL_Alchemy/UserInformation.db")

        if not db.open():
            print("Error: Could not open database connection.")
        else:
            print("Database connection established.")
            print(f"Adding User {user}, with password {password}")
            user1 = User(user,password)
            session.add(user1)
            session.commit()

    def close_window(self): 
        exit()

    def centerOnScreen (self):
        screen = self.screen()  
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        x = (geometry.width() - self.width()) // 2
        y = (geometry.height() - self.height()) // 2
        self.move(x, y) 