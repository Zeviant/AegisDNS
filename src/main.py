import sys
import json
from PySide6.QtWidgets import QApplication
from src.gui.Autentication_Window import Start_Window

def main():
    app = QApplication(sys.argv)
    
    # --- 1. Read the JSON and dynamically look up the Current Theme ---
    try:
        with open("src/gui/Style_Sheet/themes.json", "r") as f:
            themes = json.load(f)
            
        # Get the "Current theme" dictionary block
        current_theme_block = themes.get("Current theme", {})
        
        # Extract the key name (e.g., "Dark", "Dracula", "Light") 
        # list(...)[0] grabs the first key name found inside that block
        if current_theme_block:
            theme_name = list(current_theme_block.keys())[0]
        else:
            theme_name = "Default"  # Fallback if "Current theme" block is empty
            
        # Extract the actual color variables for that theme
        current_theme_data = themes.get(theme_name) or themes.get("Default")
        
    except Exception as e:
        print(f"Error loading theme configuration: {e}")
        # Absolute safety fallback constants if the JSON file is missing or broken
        theme_name = "Default"
        current_theme_data = {
            "60Color": "#0f172a", "30Color": "#131f3a", "10Color": "#3b82f6",
            "buttonHover": "#2563eb", "buttonPressed": "#1e40af", "textPrimary": "#ffffff"
        }

    # --- 2. Read the QSS template and inject the theme color data ---
    try:
        with open("src/gui/Style_Sheet/SettingsStyle.qss", "r") as f:
            template_content = f.read()
        final_style = template_content.format(**current_theme_data)
        app.setStyleSheet(final_style)
    except Exception as e:
        print(f"Error reading or formatting QSS stylesheet: {e}")

    # --- 3. Run the application ---
    window = Start_Window() 
    window.show()          

    sys.exit(app.exec())      

if __name__ == "__main__":
    main()