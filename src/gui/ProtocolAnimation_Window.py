from PySide6.QtWidgets import QWidget, QApplication, QGraphicsOpacityEffect,  QLabel, QVBoxLayout
from PySide6.QtCore import QPropertyAnimation, QPoint, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup,QSize, QPauseAnimation, Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPainterPath, QPolygonF, QPen, QColor, QBrush, QFont, QFontMetrics
import sys
import math


class ArrowWidget(QWidget):
    def __init__(self, angle, parent=None):
        super().__init__(parent)

        # ---- Arrow settings ----
        self.angle = angle                  # Direction in degrees
        self.arrow_color = QColor(255, 0, 0)
        self.line_length = 45               # Total arrow length
        self.arrow_head_size = 12           # Triangle head size
        self.body_width = 6                # Body with

        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.arrow_color))

        # ---- Center of widget ----
        cx = self.width() / 2
        cy = self.height() / 2

        # ---- Direction vector ----
        angle_rad = math.radians(self.angle)
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)

        # ---- Shaft (rounded rectangle) ----
        shaft_length = self.line_length - self.arrow_head_size
        body_width = self.body_width

        shaft_cx = cx + (shaft_length / 2) * dx
        shaft_cy = cy + (shaft_length / 2) * dy

        painter.save()
        painter.translate(shaft_cx, shaft_cy)
        painter.rotate(self.angle)

        painter.drawRoundedRect(
            -shaft_length / 2,
            -body_width / 2,
            shaft_length,
            body_width,
            body_width / 2,
            body_width / 2
        )

        painter.restore()

        # ---- Arrow head (triangle) ----
        tip_x = cx + self.line_length * dx
        tip_y = cy + self.line_length * dy
        tip = QPointF(tip_x, tip_y)

        base_x = tip_x - self.arrow_head_size * dx
        base_y = tip_y - self.arrow_head_size * dy

        perp_dx = -dy
        perp_dy = dx
        half_width = self.arrow_head_size * 0.6

        left = QPointF(
            base_x + perp_dx * half_width,
            base_y + perp_dy * half_width
        )
        right = QPointF(
            base_x - perp_dx * half_width,
            base_y - perp_dy * half_width
        )

        arrow_head = QPolygonF([tip, left, right])
        painter.drawPolygon(arrow_head)

class TitleWidget(QWidget):
    """Aesthetic title widget with dark blue background"""
    def __init__(self, text, parent=None):
        super().__init__(parent)
        
        # Create a layout for the title
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Create label for the text
        self.title_label = QLabel(text)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # Set font styling
        font = QFont("Segoe UI Semibold", 20, QFont.Bold)
        self.title_label.setFont(font)
        
        # Set text color to white for contrast
        self.title_label.setStyleSheet("color: white;")
        
        layout.addWidget(self.title_label)
        
        # Set background color (dark blue)
        self.setStyleSheet("""
            QWidget {
                background-color: #2563eb;
                border-radius: 8px;
            }
        """)
        
        # Set fixed height based on content
        font_metrics = QFontMetrics(font)
        text_height = font_metrics.height()
        self.setFixedHeight(text_height + 20)  

class ProtocolAnimation_Window(QWidget):
    def __init__(self):
        super().__init__()
        # --- Window's Settings ---
        self.resize(600, 600)
        self.setStyleSheet("QWidget {background-color: #101e29; color: #e5e7eb; font-family: Segoe UI; font-size: 14px}")

        # --- Define protocol ---
        protocol = "TCP" # later change to receive this from the sidebar
        if protocol == "TCP": 
            self.animationTCP()
        elif protocol == "UDP":
            self.animationUDP()
        else:
            print("Unknown protocol")

    def animationTCP(self):
        # --- Creation of Models ---
        # Arrow Packet Sender Model 
        self.packetSenderModel = ArrowWidget(30, self)
        self.packetSenderModel.setGeometry(215, 240, 80, 80) 
        
        # Arrow Packet Receiver Model
        self.packetReceiverModel = ArrowWidget(150, self)
        self.packetReceiverModel.setGeometry(460, 310, 80, 80) 
        self.packetReceiverModel.hide()

        # Arrow Packet Sender Model
        self.packetSender2Model = ArrowWidget(30, self)
        self.packetSender2Model.setGeometry(215, 380, 80, 80) 

        # Left Line Model
        self.lineLModel = QWidget(self)
        self.lineLModel.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineLModel.setGeometry(250, 200, 6, 400)

        # Right Line Model
        self.lineRModel = QWidget(self)
        self.lineRModel.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineRModel.setGeometry(500, 200, 6, 400)
        
        # --- Create Title Widgets ---
        # Sender title 
        self.sender_title = TitleWidget("Sender", self)
        title_width = 100
        sender_x = 250 - (title_width - 6) // 2 
        self.sender_title.setGeometry(sender_x, 100, title_width, 40)
        
        # Receiver title 
        self.receiver_title = TitleWidget("Receiver", self)
        receiver_x = 500 - (title_width - 6) // 2 
        self.receiver_title.setGeometry(receiver_x, 100, title_width, 40)

        # --- Animation ---
        # Animation Packet Sender
        self.packetAnimation = QPropertyAnimation(self.packetSenderModel, b"pos")
        self.packetAnimation.setEasingCurve(QEasingCurve.OutCubic)
        self.packetAnimation.setStartValue(QPoint(215, 240))
        self.packetAnimation.setEndValue(QPoint(425, 290))
        self.packetAnimation.setDuration(1200)

        # Animation Packet Receiver
        self.packetAnimation2 = QPropertyAnimation(self.packetReceiverModel, b"pos")
        self.packetAnimation2.setEasingCurve(QEasingCurve.InOutCubic)
        self.packetAnimation2.setStartValue(QPoint(460, 310))
        self.packetAnimation2.setEndValue(QPoint(250, 360))
        self.packetAnimation2.setDuration(1200)

        # Animation Packet Sender 2
        self.packetAnimation3 = QPropertyAnimation(self.packetSender2Model, b"pos")
        self.packetAnimation3.setEasingCurve(QEasingCurve.OutCubic)
        self.packetAnimation3.setStartValue(QPoint(250, 380))
        self.packetAnimation3.setEndValue(QPoint(425, 430))
        self.packetAnimation3.setDuration(1200)

        # Animation group
        self.packetSenderModel.show()
        self.packetReceiverModel.hide()
        self.packetSender2Model.hide()
        self.packetAnimation.finished.connect(self._on_sender_finished)
        self.packetAnimation2.finished.connect(self._on_receiver_finished)
        self.anim_group = QSequentialAnimationGroup()
       
        self.anim_group.addAnimation(QPauseAnimation(500))  # Delay
        self.anim_group.addAnimation(self.packetAnimation)
        
        self.anim_group.addAnimation(QPauseAnimation(500))  # Delay
        self.anim_group.addAnimation(self.packetAnimation2)

        self.anim_group.addAnimation(QPauseAnimation(500))  # Delay
        self.anim_group.addAnimation(self.packetAnimation3)

        self.anim_group.setLoopCount(-1) # Loop
        self.anim_group.currentLoopChanged.connect(self._on_loop_restart)
        self.anim_group.start()

    def animationUDP(self):
        pass

    def _on_sender_finished(self):
        self.packetReceiverModel.show()

    def _on_receiver_finished(self):
        self.packetSender2Model.show()

    def _on_loop_restart(self, loop):
        # Hide everything first
        self.packetSenderModel.hide()
        self.packetReceiverModel.hide()
        self.packetSender2Model.hide()

        # Reset positions
        self.packetSenderModel.move(215, 240)
        self.packetReceiverModel.move(460, 310)
        self.packetSender2Model.move(215, 380)

        # Show sender to start next loop
        self.packetSenderModel.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProtocolAnimation_Window()  
    window.show()          
    sys.exit(app.exec())