import sys, json
from PySide6.QtWidgets import QApplication


from src.gui.Autentication_Window import Start_Window
def main():
    app = QApplication(sys.argv)
    with open("src/gui/Style_Sheet/themes.json", "r") as f:
            themes = json.load(f)
            theme_name = "Default"
            current_theme_data = themes.get(theme_name)

    with open("src/gui/Style_Sheet/SettingsStyle.qss", "r") as f:
            template_content = f.read()

    final_style = template_content.format(**current_theme_data)
    
    window = Start_Window() 
    app.setStyleSheet(final_style)      
    window.show()          

    sys.exit(app.exec())      

if __name__ == "__main__":
    main()