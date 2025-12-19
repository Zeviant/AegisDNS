import random
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QAreaSeries, QSplineSeries
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush


class LiveChart(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Live Risk Activity Monitor")
        self.resize(800, 400)

        # --- Create the data series ---
        self.series = QLineSeries()
        self.series.setName("Risk-weighted activity")
        self.series.setColor(QColor("#FFFFFF"))

        # --- Set the baseline to fill the area below the plot line ---
        self.baseline = QLineSeries()
        # self.baseline = QSplineSeries()

        # --- Create the chart ---
        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.legend().hide()
        self.chart.setBackgroundBrush(QColor("#000035"))
        self.chart.setPlotAreaBackgroundBrush(QColor("#000035"))
        self.chart.setPlotAreaBackgroundVisible(True)

        # --- X axis ---
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 59)
        self.axis_x.setLabelFormat("%d")
        self.axis_x.setTitleText("Last 60 seconds")
        self.axis_x.setLabelsColor(QColor("#FFFFFF"))
        self.axis_x.setTitleBrush(QBrush(QColor("#FFFFFF")))

        # --- Y axis ---
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Incoming Packets")
        self.axis_y.setLabelsColor(QColor("#FFFFFF"))
        self.axis_y.setTitleBrush(QBrush(QColor("#FFFFFF")))

        # --- Add x and y axis to the chart ---
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)


        # --- Line Modifications ---
        plotLine = QPen(QColor("#FFFFFF"))
        plotLine.setWidth(3)
        plotLine.setCapStyle(Qt.RoundCap)     
        plotLine.setJoinStyle(Qt.RoundJoin) 
        self.series.setPen(plotLine)

        # --- Fill the area below the plot line---
        self.area = QAreaSeries(self.series, self.baseline)
        self.area.setBrush(QBrush(QColor(255, 255, 255, 60))) 
        self.area.setPen(Qt.NoPen)
        self.chart.addSeries(self.area)
        self.area.attachAxis(self.axis_x)
        self.area.attachAxis(self.axis_y)
        self.axis_y.setRange(0, 100)
        self.axis_y.setLabelFormat("%d")
        self.axis_y.setTickCount(6)

        # --- Chart view ---
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.setCentralWidget(self.chart_view)

        # --- Data storage ---
        self.max_points = 60
        self.x = 0

        # --- Timer for live updates ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(1000)

    def update_chart(self):
        y = random.uniform(0, 99)

        self.series.append(self.x, y)
        self.baseline.append(self.x, 0)  

        if self.series.count() > self.max_points:
            self.series.remove(0)
            self.baseline.remove(0)

        self.x += 1
        self.axis_x.setRange(max(0, self.x - self.max_points), self.x)

