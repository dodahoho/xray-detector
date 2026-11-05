from PySide6.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget

from xray_detector.config import AppConfig
from xray_detector.dataset.store import DatasetStore
from xray_detector.ui.annotation_view import AnnotationView
from xray_detector.ui.detection_view import DetectionView
from xray_detector.ui.training_view import TrainingView


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("X-ray detector")
        self.store = DatasetStore(config.dataset_dir, config.classes)

        self.detection_view = DetectionView(config)
        self.annotation_view = AnnotationView(config, self.store)
        self.training_view = TrainingView(config, self.store)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.detection_view, "Detektion")
        self.tabs.addTab(self.annotation_view, "Annotation")
        self.tabs.addTab(self.training_view, "Träning")
        self.tabs.setTabEnabled(1, False)
        self.setCentralWidget(self.tabs)

        self.detection_view.capture_requested.connect(self._on_capture)
        self.detection_view.error_occurred.connect(self._show_status)
        self.annotation_view.saved.connect(self._on_annotation_saved)
        self.annotation_view.cancelled.connect(self._on_annotation_cancelled)
        self.training_view.training_started.connect(self._on_training_started)
        self.training_view.training_finished.connect(self._on_training_finished)
        self.training_view.status_changed.connect(self._show_status)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("Klar")
        self.status.addWidget(self.status_label)

    def _show_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _on_capture(self, captures) -> None:
        self.annotation_view.load_captures(captures)
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

    def _on_annotation_saved(self) -> None:
        self.tabs.setTabEnabled(1, False)
        self.tabs.setCurrentIndex(0)
        self.training_view.refresh_versions()
        self._show_status("Annoteringar sparade till dataset")

    def _on_annotation_cancelled(self) -> None:
        self.tabs.setTabEnabled(1, False)
        self.tabs.setCurrentIndex(0)

    def _on_training_started(self) -> None:
        self.detection_view.pause_detection()
        self._show_status("Träning pågår – detektion pausad")

    def _on_training_finished(self) -> None:
        self.detection_view.resume_detection()
        self._show_status("Träning avslutad – detektion återupptagen")

    def closeEvent(self, event) -> None:
        self.detection_view.stop()
        super().closeEvent(event)
