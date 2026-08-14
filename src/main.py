import json
import os
import sys

from PySide6.QtCore import QEventLoop, QThread, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from src.gui.Autentication_Window import Start_Window
from src.logic import backend_launcher


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Example usage for your database:
db_path = resource_path("database.sqlite")
config_path = resource_path("config.json")


class _BackendStartupThread(QThread):
    """Runs backend_launcher.ensure_backend_running() off the UI thread so the
    splash screen stays responsive while Docker builds/starts the backend."""

    status = Signal(str)
    finished_with_result = Signal(bool, str)

    def run(self):
        ok, message = backend_launcher.ensure_backend_running(on_status=self.status.emit)
        self.finished_with_result.emit(ok, message)


def _start_backend_with_splash(app: QApplication) -> None:
    """Show a splash screen while the Dockerized backend comes up, so a
    non-technical user just double-clicks the app and waits — no terminal,
    no knowing `docker compose up -d` exists. Non-fatal on failure: the login
    window already has its own "Backend Unavailable" message box as a
    fallback, so we just warn here and let the user continue or retry."""
    logo_path = "src/images/Other_icons/AegisDNS_Logo.png"
    pixmap = QPixmap(logo_path) if os.path.isfile(logo_path) else QPixmap(400, 200)
    if pixmap.isNull():
        pixmap = QPixmap(400, 200)
        pixmap.fill(Qt.GlobalColor.darkGray)

    splash = QSplashScreen(pixmap)
    splash.showMessage(
        "Starting AegisDNS...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, Qt.GlobalColor.white
    )
    splash.show()
    app.processEvents()

    loop = QEventLoop()
    outcome = {"ok": False, "message": ""}

    thread = _BackendStartupThread()
    thread.status.connect(
        lambda msg: splash.showMessage(
            msg, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, Qt.GlobalColor.white
        )
    )

    def _on_finished(ok: bool, message: str):
        outcome["ok"] = ok
        outcome["message"] = message
        loop.quit()

    thread.finished_with_result.connect(_on_finished)
    thread.start()
    loop.exec()
    thread.wait()
    splash.close()

    if not outcome["ok"]:
        QMessageBox.warning(None, "Backend Not Started", outcome["message"])


def main():
    if getattr(sys, "frozen", False):
        # Running from a PyInstaller bundle. Every "src/..." relative-path open
        # scattered across this codebase (themes.json, icons, images, ...) assumes
        # cwd == repo root, same as when launched via `python -m src.main`. Re-create
        # that by chdir'ing into whichever bundle directory actually holds the
        # mirrored src/ tree — PyInstaller >=6 nests data files under an
        # "_internal" subfolder next to the executable by default.
        bundle_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(bundle_dir, "_internal")
        if os.path.isdir(os.path.join(internal_dir, "src")):
            os.chdir(internal_dir)
        else:
            os.chdir(bundle_dir)

    app = QApplication(sys.argv)
    _start_backend_with_splash(app)

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
