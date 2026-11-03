"""Main application window and mode switching."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from xray_detector.application.dataset_service import DatasetService
from xray_detector.application.model_registry import ModelRegistry
from xray_detector.application.training_service import TrainingService
from xray_detector.config import AppConfig
from xray_detector.domain.detection import CaptureSnapshot
from xray_detector.ui.dialogs.export_dialog import ExportDialog
from xray_detector.ui.dialogs.settings_dialog import SettingsDialog
from xray_detector.ui.pipeline import DetectionPipeline
from xray_detector.ui.views.annotation_view import AnnotationView
from xray_detector.ui.views.detection_view import DetectionView
from xray_detector.ui.views.training_view import TrainingView

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.setWindowTitle("X-ray detector")
        self.resize(1440, 900)

        self.dataset_service = DatasetService(config)
        self.model_registry = ModelRegistry(config)
        self.pipeline = DetectionPipeline(config)
        self.training_service = TrainingService(config, self.dataset_service)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.detection_view = DetectionView(config, self.model_registry, self.pipeline)
        self.training_view = TrainingView(
            config,
            self.dataset_service,
            self.model_registry,
            self.training_service,
        )
        self.stack.addWidget(self.detection_view)
        self.stack.addWidget(self.training_view)
        self._annotation_view: AnnotationView | None = None
        self._detection_was_running = False
        self._startup_done = False

        self._create_actions()
        self._create_menus()
        self.statusBar().showMessage("Redo")

        self.detection_view.capture_requested.connect(self.enter_annotation)
        self.training_view.training_about_to_start.connect(self._on_training_about_to_start)
        self.training_view.training_finished.connect(self._on_training_finished)
        self.setWindowTitle(f"X-ray detector – dataset: {config.app.dataset}")

    def _create_actions(self) -> None:
        self.action_detection = QAction("Detektionsläge", self)
        self.action_detection.setShortcut(QKeySequence("Ctrl+1"))
        self.action_detection.triggered.connect(self.show_detection)

        self.action_training = QAction("Träningsläge", self)
        self.action_training.setShortcut(QKeySequence("Ctrl+2"))
        self.action_training.triggered.connect(self.show_training)

        self.action_settings = QAction("Inställningar...", self)
        self.action_settings.setShortcut(QKeySequence("Ctrl+,"))
        self.action_settings.triggered.connect(self.open_settings)

        self.action_export = QAction("Exportera dataset...", self)
        self.action_export.triggered.connect(self.open_export)

        self.action_fullscreen = QAction("Fullscreen", self)
        self.action_fullscreen.setCheckable(True)
        self.action_fullscreen.setShortcut(QKeySequence("F11"))
        self.action_fullscreen.triggered.connect(self.toggle_fullscreen)

        self.action_quit = QAction("Avsluta", self)
        self.action_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self.action_quit.triggered.connect(self.close)

        self.action_about = QAction("Om", self)
        self.action_about.triggered.connect(self._about)

        self._exit_shortcut = QShortcut(QKeySequence(self.config.ui.exit_shortcut), self)
        self._exit_shortcut.activated.connect(self.close)

    def _create_menus(self) -> None:
        menu_mode = self.menuBar().addMenu("Läge")
        menu_mode.addAction(self.action_detection)
        menu_mode.addAction(self.action_training)
        menu_mode.addSeparator()
        menu_mode.addAction(self.action_quit)

        menu_tools = self.menuBar().addMenu("Verktyg")
        menu_tools.addAction(self.action_settings)
        menu_tools.addAction(self.action_export)

        menu_view = self.menuBar().addMenu("Visa")
        menu_view.addAction(self.action_fullscreen)

        menu_help = self.menuBar().addMenu("Hjälp")
        menu_help.addAction(self.action_about)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._apply_window_mode()
        if not self._startup_done:
            self._startup_done = True
            if self.config.ui.start_detection_on_launch:
                QTimer.singleShot(150, self.detection_view.start_detection)

    def _apply_window_mode(self) -> None:
        if self.config.ui.kiosk:
            self.menuBar().hide()
            self.statusBar().hide()
            self.showFullScreen()
            self.action_fullscreen.setChecked(True)
        else:
            self.menuBar().show()
            self.statusBar().show()
            if self.config.ui.fullscreen:
                self.showFullScreen()
                self.action_fullscreen.setChecked(True)
            else:
                self.showNormal()
                self.action_fullscreen.setChecked(False)
        if self.config.ui.show_cursor:
            self.unsetCursor()
        else:
            self.setCursor(Qt.CursorShape.BlankCursor)

    def toggle_fullscreen(self, checked: bool) -> None:
        if self.config.ui.kiosk:
            return
        self.config.ui.fullscreen = checked
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and not self.config.ui.kiosk and self.isFullScreen():
            self.config.ui.fullscreen = False
            self.showNormal()
            self.action_fullscreen.setChecked(False)
            event.accept()
            return
        super().keyPressEvent(event)

    def show_detection(self) -> None:
        if self._annotation_view is not None:
            answer = QMessageBox.question(
                self,
                "Lämna annotering",
                "Annoteringen är inte sparad. Vill du lämna läget?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._discard_annotation(restart=False)
        self.stack.setCurrentWidget(self.detection_view)
        if not self.pipeline.is_running and not self.training_service.is_running:
            self.detection_view.start_detection()

    def show_training(self) -> None:
        if self._annotation_view is not None:
            answer = QMessageBox.question(
                self,
                "Lämna annotering",
                "Annoteringen är inte sparad. Vill du lämna läget?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._discard_annotation(restart=False)
        self.training_view.refresh_datasets()
        self.training_view.refresh_models()
        self.stack.setCurrentWidget(self.training_view)

    def enter_annotation(self, snapshot: CaptureSnapshot) -> None:
        self.pipeline.stop()
        class_names = set(self.dataset_service.category_names())
        for detections in snapshot.detections.values():
            for detection in detections:
                class_names.add(detection.class_name)
        view = AnnotationView(
            snapshot,
            self.config,
            self.dataset_service,
            sorted(class_names, key=str.lower),
        )
        view.saved.connect(self._on_annotation_saved)
        view.cancelled.connect(self._on_annotation_cancelled)
        self._annotation_view = view
        self.stack.addWidget(view)
        self.stack.setCurrentWidget(view)
        self.statusBar().showMessage(f"Annoterar bildpar {snapshot.pair_id}")

    def _on_annotation_saved(self, summary) -> None:
        self.statusBar().showMessage(
            f"Sparat {summary.version}: {summary.image_count} bilder, "
            f"{summary.annotation_count} objekt"
        )
        self._remove_annotation_view()
        self.stack.setCurrentWidget(self.detection_view)
        self.detection_view.start_detection()
        self.training_view.refresh_datasets()

    def _on_annotation_cancelled(self) -> None:
        self._remove_annotation_view()
        self.stack.setCurrentWidget(self.detection_view)
        self.statusBar().showMessage("Annotering avbruten")
        self.detection_view.start_detection()

    def _discard_annotation(self, restart: bool = True) -> None:
        self._remove_annotation_view()
        self.stack.setCurrentWidget(self.detection_view)
        if restart:
            self.detection_view.start_detection()

    def _remove_annotation_view(self) -> None:
        if self._annotation_view is None:
            return
        view = self._annotation_view
        self._annotation_view = None
        self.stack.removeWidget(view)
        view.deleteLater()

    def _on_training_about_to_start(self) -> None:
        self._detection_was_running = self.pipeline.is_running
        self.pipeline.stop()
        self.statusBar().showMessage("Detektionen pausad under träning")

    def _on_training_finished(self, success: bool, message: str) -> None:
        self.statusBar().showMessage(message)
        self.training_view.refresh_datasets()
        should_restart = self._detection_was_running and (
            not success or self.stack.currentWidget() is self.detection_view
        )
        if should_restart:
            self.detection_view.start_detection()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            return
        self.model_registry.refresh()
        self.detection_view.populate_models()
        self.training_view.refresh_models()
        self.training_view.refresh_datasets()
        self._apply_window_mode()
        self._exit_shortcut.setKey(QKeySequence(self.config.ui.exit_shortcut))
        self.setWindowTitle(f"X-ray detector – dataset: {self.config.app.dataset}")
        if self.pipeline.is_running:
            self.detection_view.stop_detection()
            self.detection_view.start_detection()
        self.statusBar().showMessage("Inställningar sparade")

    def open_export(self) -> None:
        dialog = ExportDialog(self.config, self.dataset_service, self)
        dialog.exec()

    def _about(self) -> None:
        QMessageBox.information(
            self,
            "Om X-ray detector",
            "X-ray detector\n\nDetektion, annotering och träning av objektmodeller "
            "för röntgenvideoströmmar.\n\nModeller: Ultralytics YOLO och RF-DETR.",
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.training_service.is_running:
            answer = QMessageBox.question(
                self,
                "Träning pågår",
                "Träning pågår. Vill du stoppa träningen och avsluta?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.training_service.stop()
        self.pipeline.stop()
        self.config.save()
        event.accept()
