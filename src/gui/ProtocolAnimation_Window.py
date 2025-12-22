from PySide6.QtWidgets import QWidget, QApplication, QGraphicsOpacityEffect,  QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import QPropertyAnimation, QPoint, QTimer, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup,QSize, QPauseAnimation, Qt, QRectF, QPointF, Property, QAbstractAnimation
from PySide6.QtGui import QPainter, QPainterPath, QPolygonF, QPen, QColor, QBrush, QFont, QFontMetrics
import sys, random

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
        
        # Set background color 
        self.setStyleSheet("""
            QWidget {
                background-color: #2563eb;
                border-radius: 8px;
                font: 13px;
                font-weight: bold;
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
        self.setStyleSheet("""
        QLabel {
            font-size: 22px;
            font-weight: 700;
            padding: 12px 10px;
            color: #ffffff;
            background-color: #1c2839;
            border-radius: 4px;
            margin: 2px;
            border-bottom: 2px solid #2d4a6e;
        }

        QLabel#protocolLabel {
            font-size: 14px;
            font-weight: bold;
            padding: 6px 10px 8px 10px;
            color: #ffffff;
            background-color: transparent;
            border: none;
            border-bottom: 2px solid #2d4a6e;
        }

        QWidget {
            background-color: #1c2839;
            color: #e5e7eb;
            font-family: Segoe UI;
        }
        """)

        # --- Main layout ---
        layout = QVBoxLayout(self)

        # --- Title ---
        title = QLabel("Protocol Animation")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # --- Protocol variable ---
        self.protocol = "nose"
        self.packetRate = 1
        self._applied_packet_rate = self.packetRate
        self.MIN_DURATION = 300    
        self.MAX_DURATION = 1800   
        self.BASE_RATE = 50 
        self.current_duration = self.MAX_DURATION
    
        # --- Protocol label ---
        self.protocol_label = QLabel(f"Protocol: {self.protocol}")
        self.protocol_label.setObjectName("protocolLabel")
        self.protocol_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.protocol_label.adjustSize() 
        self.protocol_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self.protocol_label)

        layout.addStretch()
        # --- Creation of Variables ---
        self.displacement = 70
        self.vertical_drop = 70

        self.startPositionXSender = 255
        self.startPositionXReceiver = 480

        self.startPostionY = 200

        # --- Creation of Line ---
        # Left Line Model
        self.lineLModel = QWidget(self)
        self.lineLModel.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineLModel.setGeometry(250, 160, 6, 400)

        # Right Line Model
        self.lineRModel = QWidget(self)
        self.lineRModel.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineRModel.setGeometry(500, 160, 6, 400)
        
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

        # --- Creation of Packets ---

        # lane, direction
        self.packet_specs = [
            (0, "LR"),  # SYN
            (1, "RL"),  # SYN-ACK
            (2, "LR"),  # ACK
        ]

        self.packets = []
        for lane, direction in self.packet_specs:
            packet = QWidget(self)
            packet.setStyleSheet("background-color:#2563eb;border-radius:3.7px;")
            packet.resize(20, 20)
            packet.hide()
            self.packets.append((packet, lane, direction))

        # --- Define protocol ---
        if self.protocol == "TCP": 
            self.animationTCP()
        elif self.protocol == "UDP":
            self.animationUDP()
        else:
            print("Unknown protocol")

    def receiveProtocol(self, identifier, packetRateReceive):
        old_rate = self.packetRate

        normalized_rate = packetRateReceive / self.BASE_RATE

        raw_duration = self.MAX_DURATION / (1.0 + normalized_rate)

        # Clamp for safety
        duration = max(self.MIN_DURATION, min(self.MAX_DURATION, raw_duration))

        self.current_duration = duration


        self.current_duration = duration


        print(f"Duration was {1200 * old_rate}")
        print(f"Now Duration is {1200 * self.packetRate}")

        # Detect meaningful rate change
        rate_changed = abs(self.packetRate - self._applied_packet_rate) > 0.2

        protocol_changed = identifier != self.protocol

        if not protocol_changed and not rate_changed:
            return

        self.protocol = identifier
        self._applied_packet_rate = self.packetRate

        # --- Update label ---
        self.protocol_label.setText(f"Protocol: {self.protocol}")
        self.protocol_label.adjustSize()

        # --- Stop previous animation safely ---
        if hasattr(self, "anim_group"):
            self.anim_group.stop()
            self.anim_group.deleteLater()
            for packet, _, _ in self.packets:
                packet.hide()

        # --- Restart correct animation ---
        if self.protocol == "TCP":
            self.animationTCP()
        elif self.protocol == "UDP":
            self.animationUDP()
            
    def lane_y(self, lane):
        return self.startPostionY + lane * self.displacement

    def start_x(self, direction):
        return self.startPositionXSender if direction == "LR" else self.startPositionXReceiver

    def end_x(self, direction):
        return self.startPositionXReceiver if direction == "LR" else self.startPositionXSender
    
    def animationTCP(self):
        # --- Animation ---
        self.anim_group = QSequentialAnimationGroup()
        for packet, lane, direction in self.packets:
            y = self.lane_y(lane)
            packet.move(self.start_x(direction), y)

            anim = QPropertyAnimation(packet, b"pos")
            anim.stateChanged.connect(
                lambda newState, oldState, p=packet:
                    p.show() if newState == QAbstractAnimation.Running else None
            )
            duration = int(self.current_duration)
            print(f"The durationis now {duration}")
            anim.setDuration(duration)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(QPoint(self.start_x(direction), y))
            anim.setEndValue(QPoint(self.end_x(direction), y + self.vertical_drop))
            anim.finished.connect(packet.hide)
            self.anim_group.addAnimation(anim)

        self.anim_group.setLoopCount(-1)
        self.anim_group.currentLoopChanged.connect(self._on_loop_restart)
        self.anim_group.start()

    def animationUDP(self):
         # --- Animation ---
        self.anim_group = QSequentialAnimationGroup()

        # Build 6 UDP packets per loop
        udp_sequence = []

        for i in range(6):
            packet, lane, _ = random.choice(self.packets)

            # Mostly LR, sometimes RL
            direction = "LR" if random.random() < 0.7 else "RL"

            udp_sequence.append((packet, lane, direction))

        # Randomize order
        random.shuffle(udp_sequence)

        for packet, lane, direction in udp_sequence:
            y = self.lane_y(lane)

            packet.move(self.start_x(direction), y)

            anim = QPropertyAnimation(packet, b"pos")
            anim.stateChanged.connect(
                lambda newState, oldState, p=packet:
                    p.show() if newState == QAbstractAnimation.Running else None
            )
            duration = int(self.current_duration)
            anim.setDuration(duration)  
            anim.setEasingCurve(QEasingCurve.OutQuad)

            anim.setStartValue(QPoint(self.start_x(direction), y))
            anim.setEndValue(QPoint(self.end_x(direction), y))

            anim.finished.connect(packet.hide)

            self.anim_group.addAnimation(QPauseAnimation(random.randint(100, 400)))
            self.anim_group.addAnimation(anim)

        self.anim_group.setLoopCount(1) 
        self.anim_group.finished.connect(
            lambda: QTimer.singleShot(0, self.animationUDP)
        )
        self.anim_group.start()

    def _on_loop_restart(self, loop):
        for packet, lane, direction in self.packets:
            packet.hide()
            packet.move(self.start_x(direction), self.lane_y(lane))

        # show first packet again
        self.packets[0][0].show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProtocolAnimation_Window()  
    window.show()          
    sys.exit(app.exec())