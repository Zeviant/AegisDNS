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
        pd = (self.p / 100) * 360

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
        pen = QPen(QColor("#3b82f6"), 8)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -pd * 16)

        # ---- center text ----
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPointSize(int(side / 10))  
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(self.rect(), Qt.AlignCenter, f"{self.title} \n{self.p}%")
        self.setMinimumSize(self.sizeReceived, self.sizeReceived)
        



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





