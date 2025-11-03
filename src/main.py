import sys
from PySide6.QtWidgets import QApplication

from src.gui.Start_Window import Start_Window # 

def main():
    app = QApplication(sys.argv)
    window = Start_Window()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()