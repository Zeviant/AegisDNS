from PySide6.QtWidgets import QWidget, QApplication, QGraphicsOpacityEffect,  QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy
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
        layout_Animations = QHBoxLayout()

        
        layout_TCP = QVBoxLayout()
        layout_UDP = QVBoxLayout()

        layout_Animations.addLayout(layout_TCP)
        layout_Animations.addLayout(layout_UDP)

        # --- Title ---
        title = QLabel("Protocol Animation")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # --- Protocol General Variables ---
        # Protocol Variables
        self.animationEnded = False
        self.protocol_tcp = "TCP"
        self.protocol_udp = "UDP"
        self.dominantState = ""
        # Packet Rates Variables
        self.packetRateDominant = 1
        self._applied_packet_rateDominant = self.packetRateDominant

        self.packetRateSubservient = 1
        self._applied_packet_rateSubservient = self.packetRateSubservient

        self.duration_tcp = 1200
        self.duration_udp = 1200
        # Duration Variables
        self.MIN_DURATION = 300    
        self.MAX_DURATION = 2400   
        self.BASE_RATE = 50 
        self.current_duration = self.MAX_DURATION
    
        # --- Protocol label ---
        self.protocol_label_TCP = QLabel(f"Protocol: {self.protocol_tcp}")
        self.protocol_label_TCP.setObjectName("protocolLabel")
        self.protocol_label_TCP.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.protocol_label_TCP.adjustSize() 
        self.protocol_label_TCP.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.protocol_label_UDP = QLabel(f"Protocol: {self.protocol_udp}")
        self.protocol_label_UDP.setObjectName("protocolLabel")
        self.protocol_label_UDP.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.protocol_label_UDP.adjustSize() 
        self.protocol_label_UDP.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout_TCP.addWidget(self.protocol_label_TCP, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_UDP.addWidget(self.protocol_label_UDP, alignment=Qt.AlignmentFlag.AlignCenter)


        
        # --- Creation of Variables ---
        self.displacement = 70
        self.vertical_drop = 70

        self.startPositionXSender = 105
        self.startPositionXReceiver = 260

        self.startPostionY = 120

        # --- Creation of Line ---
        self.tcp_container = QWidget()
        self.udp_container = QWidget()

        self.tcp_container.setMinimumSize(300, 450)
        self.udp_container.setMinimumSize(300, 450)

        layout_TCP.addWidget(self.tcp_container)
        layout_UDP.addWidget(self.udp_container)

        # --- Packet counters (values provided externally every 10 seconds) ---
        counter_style = "font-size: 12px; color: #d1d5db; padding: 4px 0; background: transparent;"

        self.tcp_counter_label = QLabel("Packets received (last 10s): 0")
        self.tcp_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tcp_counter_label.setStyleSheet(counter_style)
        layout_TCP.addWidget(self.tcp_counter_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.udp_counter_label = QLabel("Packets received (last 10s): 0")
        self.udp_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.udp_counter_label.setStyleSheet(counter_style)
        layout_UDP.addWidget(self.udp_counter_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- TCP Lines ---
        # Left Line Model
        self.lineLModel_TCP = QWidget(self.tcp_container)
        self.lineLModel_TCP.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineLModel_TCP.setGeometry(100, 80, 6, 350)

        # Right Line Model
        self.lineRModel_TCP = QWidget(self.tcp_container)
        self.lineRModel_TCP.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineRModel_TCP.setGeometry(280, 80, 6, 350)

        # --- UDP Lines ---
        self.lineLModel_UDP = QWidget(self.udp_container)
        self.lineLModel_UDP.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineLModel_UDP.setGeometry(100, 80, 6, 350)

        # Right Line Model
        self.lineRModel_UDP = QWidget(self.udp_container)
        self.lineRModel_UDP.setStyleSheet("background-color:white; border-radius:3px;")
        self.lineRModel_UDP.setGeometry(280, 80, 6, 350)
        
        # --- Create Title Widgets ---
        # --- TCP ---
        # Sender title 
        self.sender_title_tcp = TitleWidget("Sender", self.tcp_container)
        title_width_tcp = 100
        sender_x_tcp = 100 - (title_width_tcp - 6) // 2 
        self.sender_title_tcp.setGeometry(sender_x_tcp, 20, title_width_tcp, 40)
        
        # Receiver title 
        self.receiver_title_tcp = TitleWidget("Receiver", self.tcp_container)
        receiver_x_tcp = 280 - (title_width_tcp - 6) // 2 
        self.receiver_title_tcp.setGeometry(receiver_x_tcp, 20, title_width_tcp, 40)

        # --- UDP ---
        # Sender title 
        self.sender_title_udp = TitleWidget("Sender", self.udp_container)
        title_width_udp = 100
        sender_x_udp = 100 - (title_width_udp - 6) // 2 
        self.sender_title_udp.setGeometry(sender_x_udp, 20, title_width_udp, 40)
        
        # Receiver title 
        self.receiver_title = TitleWidget("Receiver", self.udp_container)
        receiver_x = 280 - (title_width_udp - 6) // 2 
        self.receiver_title.setGeometry(receiver_x, 20, title_width_udp, 40)

        # --- Creation of Packets ---
        # lane, direction
        self.packet_specs = [
            (0, "LR"),  # SYN
            (1, "RL"),  # SYN-ACK
            (2, "LR"),  # ACK
        ]

        self.packets_tcp = []
        for lane, direction in self.packet_specs:
            packet = QWidget(self.tcp_container)
            packet.setStyleSheet("background-color:#2563eb;border-radius:3.7px;")
            packet.resize(20, 20)
            packet.hide()
            self.packets_tcp.append((packet, lane, direction))

        self.packets_udp = []
        for lane, direction in self.packet_specs:
            packet = QWidget(self.udp_container)
            packet.setStyleSheet("background-color:#2563eb;border-radius:3.7px;")
            packet.resize(20, 20)
            packet.hide()
            self.packets_udp.append((packet, lane, direction))

        layout.addLayout(layout_Animations)
        layout.addStretch()

        # Flags to track when animations need to be updated
        self._tcp_needs_restart = False
        self._pending_duration_tcp = self.duration_tcp
        
        self.animationUDP()
        self.animationTCP()

    def receiveProtocol(self, dominant, packetRateDominant, subservient, packetRateSubservient):
        # Update stored rates 
        self.packetRateDominant = packetRateDominant
        self.packetRateSubservient = packetRateSubservient

        # Normalize
        durationDominant = self._duration_from_packets(packetRateDominant)
        durationSubservient = self._duration_from_packets(packetRateSubservient)

        if dominant == "TCP":
            self.duration_tcp = durationDominant
            self.duration_udp = durationSubservient
        elif dominant == "UDP":
            self.duration_udp = durationDominant
            self.duration_tcp = durationSubservient
        elif dominant == "Mixed":
            self.duration_udp = durationDominant
            self.duration_tcp = durationSubservient
        else:
            return

        rate_changedDominant = abs(self.packetRateDominant - self._applied_packet_rateDominant) > 0.2
        rate_changedSubservient = abs(self.packetRateSubservient - self._applied_packet_rateSubservient) > 0.2
        dominant_changed = dominant != self.dominantState

        if not (dominant_changed or rate_changedDominant or rate_changedSubservient):
            return

        self.dominantState = dominant
        self._applied_packet_rateDominant = self.packetRateDominant
        self._applied_packet_rateSubservient = self.packetRateSubservient

        if dominant in ("TCP", "Mixed"):
            # Instead of restarting immediately, set a flag to restart after current loop
            self._tcp_needs_restart = True
            self._pending_duration_tcp = self.duration_tcp
        
        if dominant in ("UDP", "Mixed"):
            if hasattr(self, "anim_group_udp"):
                self.anim_group_udp.stop()
                self.anim_group_udp.deleteLater()
            
            self._reset_udp_packets()
            self.animationUDP()

    def _reset_tcp_packets(self):
        for packet, lane, direction in self.packets_tcp:
            packet.hide()
            packet.move(
                self.start_x(direction),
                self.lane_y(lane)
            )

    def _reset_udp_packets(self):
        for packet, lane, direction in self.packets_udp:
            packet.hide()
            packet.move(
                self.start_x(direction),
                self.lane_y(lane)
            )

    def _duration_from_packets(self, packet_count):
        if packet_count >= 1000:
            return self.MIN_DURATION   
        elif packet_count > 100:
            return 1200
        else:
            return self.MAX_DURATION 
            
    def lane_y(self, lane):
        return self.startPostionY + lane * self.displacement

    def start_x(self, direction):
        return self.startPositionXSender if direction == "LR" else self.startPositionXReceiver

    def end_x(self, direction):
        return self.startPositionXReceiver if direction == "LR" else self.startPositionXSender
    
    def animationTCP(self):
        # --- Animation ---
        self.anim_group_tcp = QSequentialAnimationGroup()
        
        for packet, lane, direction in self.packets_tcp:
            y = self.lane_y(lane)
            packet.move(self.start_x(direction), y)
            
            anim = QPropertyAnimation(packet, b"pos")
            anim.stateChanged.connect(
                lambda newState, oldState, p=packet:
                    p.show() if newState == QAbstractAnimation.Running else None
            )
            
            duration = int(self.duration_tcp)
            anim.setDuration(duration)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(QPoint(self.start_x(direction), y))
            anim.setEndValue(QPoint(self.end_x(direction), y + self.vertical_drop))
            anim.finished.connect(packet.hide)
            self.anim_group_tcp.addAnimation(anim)
        
        # Connect finished signal to handle loop completion
        self.anim_group_tcp.finished.connect(self._on_tcp_animation_finished)
        self.anim_group_tcp.setLoopCount(1)  # Set to 1, we'll manually restart to check for updates
        self.anim_group_tcp.start()

    def _on_tcp_animation_finished(self):
        # Check if we need to restart with new duration
        if self._tcp_needs_restart:
            self._tcp_needs_restart = False
            self.duration_tcp = self._pending_duration_tcp
            
            # Clean up old animation
            if hasattr(self, "anim_group_tcp"):
                self.anim_group_tcp.deleteLater()
            
            # Reset packets to starting positions
            self._reset_tcp_packets()
            
            # Start new animation with updated duration
            self.animationTCP()
        else:
            # Continue with same duration
            if hasattr(self, "anim_group_tcp"):
                self.anim_group_tcp.deleteLater()
            
            # Reset packets to starting positions
            self._reset_tcp_packets()
            
            # Restart animation
            self.animationTCP()

    def animationUDP(self):
         # --- Animation ---
        self.anim_group_udp = QSequentialAnimationGroup()

        # Build 6 UDP packets per loop
        udp_sequence = []

        for i in range(6):
            packet, lane, _ = random.choice(self.packets_udp)

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
            duration = int(self.duration_udp)
            anim.setDuration(duration)  
            anim.setEasingCurve(QEasingCurve.OutQuad)

            anim.setStartValue(QPoint(self.start_x(direction), y))
            anim.setEndValue(QPoint(self.end_x(direction), y))

            anim.finished.connect(packet.hide)

            self.anim_group_udp.addAnimation(QPauseAnimation(random.randint(100, 400)))
            self.anim_group_udp.addAnimation(anim)

        self.anim_group_udp.setLoopCount(1) 
        self.anim_group_udp.finished.connect(
            lambda: QTimer.singleShot(0, self.animationUDP)
        )
        self.anim_group_udp.start()

    def update_packet_counts(self, tcp_count: int, udp_count: int):
        # use real sniffer data to update the packet counters
        self.tcp_counter_label.setText(f"TCP packets (last 10s): {int(tcp_count)}")
        self.udp_counter_label.setText(f"UDP packets (last 10s): {int(udp_count)}")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProtocolAnimation_Window()  
    window.show()          
    sys.exit(app.exec())