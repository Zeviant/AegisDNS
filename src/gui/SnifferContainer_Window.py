from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, 
    QHBoxLayout, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt
import sys
from src.gui.ProtocolAnimation_Window import ProtocolAnimation_Window
from src.gui.packet_sniffer_widget import PacketSnifferWidget


class SnifferContainer_Window(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sniffer Graph & Protocol Animation")
        self.resize(600, 400)

        main_layout = QVBoxLayout(self)

        button_layout = QHBoxLayout()

        self.graph_btn = QPushButton("Sniffer Graph")
        self.graph_btn.setObjectName("TopButton")
        self.animation_btn = QPushButton("Protocol Animation")
        self.animation_btn.setObjectName("TopButton")

        self.graph_widget = PacketSnifferWidget()
        self.animation_widget = ProtocolAnimation_Window()

        self.graph_btn.clicked.connect(self.show_sniffer_graph)
        self.animation_btn.clicked.connect(self.show_protocol_animation)

        button_layout.addWidget(self.graph_btn)
        button_layout.addWidget(self.animation_btn)

        main_layout.addLayout(button_layout)

        self.stacked = QStackedWidget()

        # Page 1 — Packet Sniffer Graph
        graph_page = QWidget()
        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.graph_widget)
        graph_page.setLayout(graph_layout)

        # Page 2 — Protocol Animation
        animation_page = QWidget()
        animation_layout = QVBoxLayout()
        animation_layout.addWidget(self.animation_widget)
        animation_page.setLayout(animation_layout)

        # Add pages to stack
        self.stacked.addWidget(graph_page)  # index 0
        self.stacked.addWidget(animation_page)  # index 1

        main_layout.addWidget(self.stacked)

    def update_sniffer_data(self, snapshot):
        self.graph_widget.update_data(snapshot)

    def update_packet_counts(self, tcp_count: int, udp_count: int):
        """Pass real sniffer counts down to the animation widget."""
        self.animation_widget.update_packet_counts(tcp_count, udp_count)

    def sent_dominant_animation(self, dominant, packetRateDominant, subservient, packetRateSubservient):
        self.animation_widget.receiveProtocol(dominant, packetRateDominant, subservient, packetRateSubservient)

    def show_sniffer_graph(self):
        self.stacked.setCurrentIndex(0)

    def show_protocol_animation(self):
        self.stacked.setCurrentIndex(1)


