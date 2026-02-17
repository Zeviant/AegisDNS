from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QVBoxLayout, QWidget

class CPBar(QWidget):
    def __init__(self):
        super().__init__()
        self.p = 0  
        self.setMinimumSize(208, 208)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setValue(self, value: int):
        value = max(0, min(100, value))

        if self.p == value:
            return

        self.p = value
        self.update()

    def paintEvent(self, e):
        pd = (self.p / 100) * 360

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(4, 4)

        pathBackground = QPainterPath()
        pathBackground.moveTo(100, 0)
        pathBackground.arcTo(QRectF(0, 0, 200, 200), 90, 360 )

        penBackground = QPen()
        penBackground.setCapStyle(Qt.RoundCap)
        penBackground.setColor(QColor("#0f172a"))
        penBackground.setWidth(8)

        painter.strokePath(pathBackground, penBackground)

        path = QPainterPath()
        path.moveTo(100, 0)
        path.arcTo(QRectF(0, 0, 200, 200), 90, -pd)

        pen = QPen()
        pen.setCapStyle(Qt.RoundCap)
        pen.setColor(QColor("#3b82f6"))
        pen.setWidth(8)

        painter.strokePath(path, pen)

        painter.resetTransform()

        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(self.rect(), Qt.AlignCenter, f"Total Score \n{self.p}%")


class CircularGraph(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.progress = CPBar()
        layout.addWidget(self.progress)

        self.value = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.increase)
        self.timer.start(50)

    def increase(self):
        self.value += 1
        if self.value > 40:
            return

        self.progress.setValue(self.value)



