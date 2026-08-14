from PySide6.QtCore import QObject, Signal, QThread
import time

class SnifferWorker(QObject):
    data_ready = Signal(list)  # emits aggregated snapshot
    error = Signal(str)  # emits a raw capture-start error (e.g. permission denied)

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
