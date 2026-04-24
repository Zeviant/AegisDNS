from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtCore import Qt
from src.logic.llm_service import ModelDownloadThread


class ModelDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Model Required")
        self.setFixedWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("AI Model Not Found")
        title.setObjectName("TitleTables")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "The AI Overview feature requires a local language model (~2 GB).\n"
            "(Llama 3.2 3B Instruct)\n"
            "This is a one-time download. The model runs entirely on your device."
        )
        desc.setWordWrap(True)
        desc.setObjectName("Subtitle")
        layout.addWidget(desc)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setObjectName("scanProgress")
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("Subtitle")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        self.download_btn = QPushButton("Download Model")
        self.download_btn.setObjectName("ScannerButton")
        self.download_btn.clicked.connect(self._start_download)
        layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

    def _start_download(self):
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Starting download...")

        self._thread = ModelDownloadThread(self)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished.connect(self._on_finished)
        self._thread.start()

    def _on_progress(self, percent: int, downloaded_mb: float, total_mb: float):
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"Downloading... {downloaded_mb:.0f} MB / {total_mb:.0f} MB")

    def _on_finished(self, success: bool, error_msg: str):
        if success:
            self.accept()
        else:
            self.status_label.setText(f"Download failed: {error_msg}")
            self.download_btn.setEnabled(True)
            self.download_btn.setText("Retry Download")
            self.cancel_btn.setEnabled(True)
