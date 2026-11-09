from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStatusBar, QTabWidget

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.config import AppConfig
from xray_detector.ui.annotation_view import AnnotationView
from xray_detector.ui.dataset_view import DatasetView
from xray_detector.ui.detection_view import DetectionView
from xray_detector.ui.settings_view import SettingsView
from xray_detector.ui.theme import apply_theme
from xray_detector.ui.training_view import TrainingView


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("X-ray detector")
        self.dataset_service = DatasetService(config.dataset_dir, config.classes)
        self.settings = QSettings(
            str(config.data_dir / "settings.ini"), QSettings.Format.IniFormat
        )
        if self.settings.contains("window/width"):
            self.setGeometry(
                int(self.settings.value("window/x", type=int)),
                int(self.settings.value("window/y", type=int)),
                int(self.settings.value("window/width", type=int)),
                int(self.settings.value("window/height", type=int)),
            )

        self.detection_view = DetectionView(config, self.settings)
        self.annotation_view = AnnotationView(config, self.dataset_service, self.settings)
        self.dataset_view = DatasetView(self.dataset_service)
        self.training_view = TrainingView(config, self.dataset_service, self.settings)
        self.settings_view = SettingsView(self.settings)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.detection_view, "Detektion")
        self.tabs.addTab(self.annotation_view, "Annotation")
        self.tabs.addTab(self.dataset_view, "Dataset")
        self.tabs.addTab(self.training_view, "Träning")
        self.tabs.addTab(self.settings_view, "Inställningar")
        self.tabs.setTabEnabled(1, False)
        self.setCentralWidget(self.tabs)
        self.detection_view.restore_settings()
        self.annotation_view.restore_settings()
        self.training_view.restore_settings()

        self.detection_view.capture_requested.connect(self._on_capture)
        self.detection_view.error_occurred.connect(self._show_status)
        self.annotation_view.saved.connect(self._on_annotation_saved)
        self.annotation_view.cancelled.connect(self._on_annotation_cancelled)
        self.training_view.training_started.connect(self._on_training_started)
        self.training_view.training_finished.connect(self._on_training_finished)
        self.training_view.status_changed.connect(self._show_status)
        self.dataset_view.open_annotation_requested.connect(self._on_capture)
        self.dataset_view.status_changed.connect(self._show_status)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("Klar")
        self.status.addWidget(self.status_label)

        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

        self.detection_view.check_device()
        apply_theme(
            QApplication.instance(),
            self.settings.value("ui/theme", "system", type=str),
        )

    def show_window(self) -> None:
        if self.settings.value("window/maximized", True, type=bool):
            self.showMaximized()
        else:
            self.show()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
        else:
            self.showFullScreen()

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
        self.dataset_view.refresh()
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
        geometry = self.normalGeometry() if self.isFullScreen() or self.isMaximized() else self.geometry()
        self.settings.setValue("window/x", geometry.x())
        self.settings.setValue("window/y", geometry.y())
        self.settings.setValue("window/width", geometry.width())
        self.settings.setValue("window/height", geometry.height())
        self.settings.setValue(
            "window/maximized", self.isMaximized() and not self.isFullScreen()
        )
        self.detection_view.save_settings()
        self.annotation_view.save_settings()
        self.training_view.save_settings()
        self.settings.sync()
        self.detection_view.stop()
        super().closeEvent(event)
