# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'login.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QLabel, QLineEdit, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QStatusBar,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(309, 484)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        MainWindow.setFont(font)
        MainWindow.setStyleSheet(u"QPushButton #pushButton{\n"
"background-color: rgba(2, 65, 118, 255); \n"
"color: rgba(255, 255, 255, 200);\n"
"border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton #pushButton:pressed{\n"
"padding-left: 5px;\n"
"padding-right: 5px;\n"
"background-color: rgba(2, 65, 118, 100); \n"
"background-position: calc(100% - 10px) center;\n"
"}\n"
"\n"
"QPushButton #pushButton{\n"
"background-color: rgba(2, 65, 118, 200); \n"
"}")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.widget = QWidget(self.centralwidget)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(10, 10, 290, 410))
        self.widget.setStyleSheet(u"QPushButton#pushButton {\n"
"    background-color: rgba(2,65,118,255);\n"
"    color: rgba(255,255,255,200);\n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton#pushButton:pressed {\n"
"    padding-left: 5px;   /* gives a \u201cpressed\u201d shove */\n"
"    padding-top: 2px;    /* optional */\n"
"    background-color: rgba(2,65,118,100);\n"
"}\n"
"\n"
"QPushButton#pushButton:hover {\n"
"    background-color: rgba(2,65,118,200);\n"
"}\n"
"")
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(0, 0, 290, 410))
        self.label.setStyleSheet(u"background-color: rgba(16, 30, 41, 240);\n"
"border-radius: 10px;")
        self.lineEdit = QLineEdit(self.widget)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setGeometry(QRect(20, 210, 250, 30))
        font1 = QFont()
        font1.setPointSize(10)
        self.lineEdit.setFont(font1)
        self.lineEdit.setStyleSheet(u"background-color: rgba(0, 0, 0, 0);\n"
"border: 1px solid rgba(0, 0, 0, 0);\n"
"border-bottom-color: rgba(46, 82, 101, 255);\n"
"color: rgb(255, 255, 255);\n"
"padding-bottom: 7px;")
        self.lineEdit_2 = QLineEdit(self.widget)
        self.lineEdit_2.setObjectName(u"lineEdit_2")
        self.lineEdit_2.setGeometry(QRect(20, 260, 250, 30))
        self.lineEdit_2.setFont(font1)
        self.lineEdit_2.setStyleSheet(u"background-color: rgba(0, 0, 0, 0);\n"
"border: 1px solid rgba(0, 0, 0, 0);\n"
"border-bottom-color: rgba(46, 82, 101, 255);\n"
"color: rgb(255, 255, 255);\n"
"padding-bottom: 7px;")
        self.lineEdit_2.setEchoMode(QLineEdit.Password)
        self.pushButton = QPushButton(self.widget)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(20, 320, 250, 40))
        font2 = QFont()
        font2.setBold(True)
        self.pushButton.setFont(font2)
        self.pushButton.setStyleSheet(u"")
        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(60, 30, 180, 150))
        self.label_2.setPixmap(QPixmap(u"C:/Users/Nico/Desktop/free-user-icon-3296-thumb.png"))
        self.label_2.setScaledContents(True)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 309, 26))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label.setText("")
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"User Name", None))
        self.lineEdit_2.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Password", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"L o g   I n", None))
        self.label_2.setText("")
    # retranslateUi

