from PySide6.QtCore import QObject, Signal, QThread
import time

class SnifferWorker(QObject):
    data_ready = Signal(list)  # emits aggregated snapshot

    def __init__(self, aggregator):
        super().__init__()
        self.aggregator = aggregator
        self.running = False

    def start(self):
        self.running = True
        while self.running:
            snapshot = self.aggregator.get_snapshot()
            self.data_ready.emit(snapshot)
            time.sleep(1)  

    def stop(self):
        self.running = False
