# src/main.py
import sys
from PySide6.QtWidgets import QApplication
from .login_window import LoginWindow

def main():
    app = QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
