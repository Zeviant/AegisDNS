from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, 
    QHBoxLayout, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt
import sys
from src.gui.WhiteList_Window import WhiteList_Window
from src.gui.BlackList_Window import BlackList_Window


class WhiteBlackList_Window(QWidget):
    def __init__(self, user_name: str):
        super().__init__()

        self.setWindowTitle("White & Black List")
        self.resize(600, 400)

        self.userName = user_name
        main_layout = QVBoxLayout(self)

        # ---------------------------
        # Top buttons
        # ---------------------------
        button_layout = QHBoxLayout()

        self.white_btn = QPushButton("White List")
        self.white_btn.setObjectName("TopButton")
        self.black_btn = QPushButton("Black List")
        self.black_btn.setObjectName("TopButton")

        self.white_btn.clicked.connect(self.show_white_list)
        self.black_btn.clicked.connect(self.show_black_list)

        button_layout.addWidget(self.white_btn)
        button_layout.addWidget(self.black_btn)

        main_layout.addLayout(button_layout)

        # ---------------------------
        # StackWidget
        # ---------------------------
        self.stacked = QStackedWidget()

        # Set stylesheet
        # Load table styling from QSS file
        # with open("src/gui/Style_Sheet/DefaultStyle.qss", "r") as f:
        #     self.setStyleSheet(f.read())

        # Page 1 — White List
        white_page = QWidget()
        white_layout = QVBoxLayout()
        white_layout.addWidget(WhiteList_Window(self.userName))
        white_page.setLayout(white_layout)

        # Page 2 — Black List
        black_page = QWidget()
        black_layout = QVBoxLayout()
        black_layout.addWidget(BlackList_Window(self.userName))
        black_page.setLayout(black_layout)

        # Add pages to stack
        self.stacked.addWidget(white_page)  # index 0
        self.stacked.addWidget(black_page)  # index 1

        main_layout.addWidget(self.stacked)

    # ---------------------------
    # Page switching
    # ---------------------------
    def show_white_list(self):
        self.stacked.setCurrentIndex(0)

    def show_black_list(self):
        self.stacked.setCurrentIndex(1)


