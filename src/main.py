import sys
from PySide6.QtWidgets import QApplication

from src.gui.Start_Window import Start_Window
def main():
    app = QApplication(sys.argv)
    with open("src/gui/Style_Sheet/Start_Window_Style.qss") as f: 
        style_str = f.read()
    
    window = Start_Window() 
    window.setStyleSheet(style_str)      
    window.show()          

    sys.exit(app.exec())      

if __name__ == "__main__":
    main()