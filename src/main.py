# src/main.py
import sys
from PySide6.QtWidgets import QApplication
from src.Start_Window import Start_Window

def main():
    app = QApplication(sys.argv)
    w = Start_Window()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
