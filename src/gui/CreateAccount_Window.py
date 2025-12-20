# --- Qt Libraries ---
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox

# --- Connection to other modules ---
from src.SQL_Alchemy.database_manager import DatabaseManager


# --- Class Creation ---
class CreateAccount_Window(QWidget): 
    # Window SetUp
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create Account Window")
        self.resize(400, 600)
        self.centerOnScreen()

        # Fixed Box Size
        contentSquare = QWidget()
        contentSquare.setFixedSize(300, 450) 

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
        full_layout.setSpacing(10)
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

        # In case some of the filds are empty
        if (self.firstName_line_edit.text() == "" or self.lastName_line_edit.text() == ""):
            fieldsEmpty_box = QMessageBox()
            fieldsEmpty_box.setWindowTitle("ERROR")
            fieldsEmpty_box.setIcon(QMessageBox.Warning)
            fieldsEmpty_box.setText("Some fields are empty!")
            fieldsEmpty_box.exec()
        
        # In case passwords does not match
        elif (password != cpassword): 
                passwordMissmatch_box = QMessageBox()
                passwordMissmatch_box.setWindowTitle("ERROR")
                passwordMissmatch_box.setIcon(QMessageBox.Warning)
                passwordMissmatch_box.setText("Passwords must match!")
                passwordMissmatch_box.exec()
        
        # If everything ok so far
        else: 
            self.addNewUserToDatabase(userName, password, firstName, lastName)

    def addNewUserToDatabase(self, userName, password, firstName, lastName): 
        # Logic is now delegated to DatabaseManager
        result = DatabaseManager.create_new_user(userName, password, firstName, lastName)
        
        if result == "taken": 
            # Display Warning Message
            userNameAlreadyExists_box = QMessageBox()
            userNameAlreadyExists_box.setWindowTitle("ERROR")
            userNameAlreadyExists_box.setIcon(QMessageBox.Warning)
            userNameAlreadyExists_box.setText("Username already taken!")
            userNameAlreadyExists_box.exec()

        # If username is not taken, add it to the database
        elif result == "success":
            successMessage_box = QMessageBox()
            successMessage_box.setWindowTitle("Success!")
            successMessage_box.setIcon(QMessageBox.Information)
            successMessage_box.setText("User created successfully")
            successMessage_box.exec()
            self.close()

        elif result == "error":
            QMessageBox.critical(self, "Database Error", "An unexpected error occurred while saving the user.")

    def close_window(self): 
        self.close()
        
    def centerOnScreen (self):
        screen = self.screen()  
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        x = (geometry.width() - self.width()) // 2
        y = (geometry.height() - self.height()) // 2
        self.move(x, y)