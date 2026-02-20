from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QVBoxLayout, QWidget

class CPBar(QWidget):
    def __init__(self):
        super().__init__()
        self.p = 0  
        self.title = ""
        self.sizeReceived = 200
        self.setMinimumSize(200, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setValue(self, value):
        value = max(0, min(100, value))

        if self.p == value:
            return

        self.p = value
        self.update()

    def setTitle(self, title):
        self.title = title
        self.update()
    
    def setSize(self, size):
        self.sizeReceived = size
        self.update

    def paintEvent(self, e):
        pd = (self.p / 60) * 360
        pde = (self.p / 30) * 360

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # ---- dynamic size ----
        margin = 8
        side = min(self.width(), self.height()) - margin
        rect = QRectF(
            (self.width() - side) / 2,
            (self.height() - side) / 2,
            side,
            side
        )

        # ---- background circle ----
        penBackground = QPen(QColor("#0f172a"), 8)
        penBackground.setCapStyle(Qt.RoundCap)
        painter.setPen(penBackground)
        painter.drawArc(rect, 0, 360 * 16)

        # ---- progress arc ----
        if self.title == "Total Score": 
            pen = QPen(QColor("#3b82f6"), 8)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -pd * 16)
        else: 
            pen = QPen(QColor("#3b82f6"), 8)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -pde * 16)

        # ---- center text ----
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPointSize(int(side / 10))  
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(self.rect(), Qt.AlignCenter, f"{self.title} \n{self.p}%")
        self.setMinimumSize(self.sizeReceived, self.sizeReceived)
        
        if self.title == "Total Score": 
            painter.setPen(QColor("#ffffff"))
            font = painter.font()
            font.setPointSize(int(side / 20))  
            font.setBold(True)
            painter.setFont(font)
            verdictRect = self.rect().adjusted(0, 0, 0, -50)

            if 0 < self.p <= 10:
                painter.drawText(verdictRect, Qt.AlignHCenter|Qt.AlignBottom, f"Verdict: SECURE")

            elif 11 <= self.p <= 20:
                painter.drawText(verdictRect, Qt.AlignHCenter|Qt.AlignBottom, f"Verdict: SAFE")

            elif 21 <= self.p <= 30:
                painter.drawText(verdictRect, Qt.AlignHCenter|Qt.AlignBottom, f"Verdict: NEUTRAL")

            elif 31 <= self.p <= 40:
                painter.drawText(verdictRect, Qt.AlignHCenter|Qt.AlignBottom, f"Verdict: CAUTION")

            elif 41 <= self.p <= 50:
                painter.drawText(verdictRect, Qt.AlignHCenter|Qt.AlignBottom, f"Verdict: SUSPICIOUS")

            elif 51 <= self.p <= 60:
                painter.drawText(verdictRect, Qt.AlignHCenter|Qt.AlignBottom, f"Verdict: DANGEROUS")

            elif 60 < self.p:
                painter.drawText(verdictRect, Qt.AlignHCenter|Qt.AlignBottom, f"Verdict: MALICIOUS")
        



class CircularGraph(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.progress = CPBar()
        layout.addWidget(self.progress)

        self.value = 0
        self.score = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.increase)
        self.timer.start(20)

    def getScore(self, scoreReceived): 
        self.score = int(abs(scoreReceived))
        
    def setTitle(self, titleReceived):
        self.progress.setTitle(titleReceived)

    def setSize(self, sizeReceived):
        self.progress.setSize(sizeReceived)
        
    def increase(self):
        if self.value < self.score:
            self.value += 1
            self.progress.setValue(self.value)

        elif self.value > self.score:
            self.value -= 1
            self.progress.setValue(self.value)





