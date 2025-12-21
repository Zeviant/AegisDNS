from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QAreaSeries

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush


class PacketSnifferWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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

        # --- Title ---
        # --- Main layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # --- Title ---
        title = QLabel("Packet Sniffer")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addStretch()

        # --- Chart title ---
        self.setMinimumHeight(350)

        # self.setStyleSheet("QWidget { background-color: #2a3a52; }")

        # --- Data series ---
        self.series = QLineSeries()
        self.series.setName("Network Activity Level")
        self.series.setColor(QColor("#FFFFFF"))

        self.baseline = QLineSeries()

        # --- Chart ---
        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.legend().hide()
        self.chart.setBackgroundBrush(QColor("#000035"))
        self.chart.setPlotAreaBackgroundBrush(QColor("#000035"))
        self.chart.setPlotAreaBackgroundVisible(True)

        # --- X axis (time) ---
        self.axis_x = QValueAxis()
        self.axis_x.setLabelFormat("%d")
        self.axis_x.setTitleText("Last 60 seconds")
        self.axis_x.setLabelsColor(QColor("#FFFFFF"))
        self.axis_x.setTitleBrush(QBrush(QColor("#FFFFFF")))
        self.axis_x.setRange(0, 59)

        # --- Y axis (activity) ---
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Activity Score")
        self.axis_y.setLabelsColor(QColor("#FFFFFF"))
        self.axis_y.setTitleBrush(QBrush(QColor("#FFFFFF")))
        self.axis_y.setRange(0, 5000)  # auto-adjusted later
        self.axis_y.setTickCount(6)

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)

        # --- Line styling ---
        pen = QPen(QColor("#FFFFFF"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.series.setPen(pen)

        # --- Area fill ---
        self.area = QAreaSeries(self.series, self.baseline)
        self.area.setBrush(QBrush(QColor(255, 255, 255, 60)))
        self.area.setPen(Qt.NoPen)
        self.chart.addSeries(self.area)
        self.area.attachAxis(self.axis_x)
        self.area.attachAxis(self.axis_y)

        # --- Chart view ---
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        
        layout.addWidget(self.chart_view, stretch=1)

        # --- Data state ---
        self.max_points = 60
        self.x_index = 0

    def update_data(self, snapshot):
        if not snapshot:
            return

        latest = snapshot[-1]
        activity_score = latest["bytes_in"] + latest["bytes_out"]

        # Append new point
        self.series.append(self.x_index, activity_score)
        self.baseline.append(self.x_index, 0)
        self.x_index += 1

        # --- x-axis: always slide ---
        if self.x_index < self.max_points:
            self.axis_x.setRange(0, self.max_points)
        else:
            self.axis_x.setRange(self.x_index - self.max_points, self.x_index)

        # --- y-axis: it has now adaptive scaling ---
        values = [p.y() for p in self.series.pointsVector()]
        max_value = max(values) if values else 1

        step = max(100, int(max_value) // 5)
        scale_max = ((int(max_value) // step) + 1) * step

        self.axis_y.setRange(0, scale_max)
        self.axis_y.setTickCount(6)

