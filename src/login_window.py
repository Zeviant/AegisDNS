# src/login_window.py
from PySide6.QtWidgets import QMainWindow
from .ui_gen.ui_login import Ui_MainWindow

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self) # connects it with ui_login.py

        # open main window on button click
        self._main = None
        self.ui.pushButton.clicked.connect(self.open_main)

    def open_main(self):
        from .main_window import MainWindow   
        self._main = MainWindow()
        self._main.show()
        self.close()  
