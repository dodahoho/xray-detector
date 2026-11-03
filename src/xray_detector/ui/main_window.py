from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolBar,
)

from xray_detector.config import AppConfig, save_config
from xray_detector.dataset.export import export_dataset
from xray_detector.dataset.pending import PendingCapture
from xray_detector.dataset.store import DatasetStore, get_or_create_store
from xray_detector.ui.annotation_view import AnnotationView
from xray_detector.ui.detection_view import DetectionView
from xray_detector.ui.export_dialog import ExportDialog
from xray_detector.ui.settings_dialog import SettingsDialog
from xray_detector.ui.training_view import TrainingView
from xray_detector.util.paths import AppPaths

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, paths: AppPaths, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.config = config
        self.paths = paths
        self.store: DatasetStore = get_or_create_store(
            paths.datasets, config.app.active_dataset
        )
        self.setWindowTitle("X-ray detector")
        self.resize(1600, 1000)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.detection_view = DetectionView(config, paths)
        self.annotation_view = AnnotationView(self.store)
        self.training_view = TrainingView(config, paths)
        self.stack.addWidget(self.detection_view)
        self.stack.addWidget(self.annotation_view)
        self.stack.addWidget(self.training_view)

        self._build_toolbar()
        self.statusBar().showMessage("Startar...")
        self.dataset_status = QLabel()
        self.statusBar().addPermanentWidget(self.dataset_status)

        self.detection_view.captureReady.connect(self._open_annotation)
        self.detection_view.statusMessage.connect(self.statusBar().showMessage)
        self.annotation_view.saved.connect(self._annotation_saved)
        self.annotation_view.cancelled.connect(self._annotation_cancelled)
        self.training_view.trainingStarted.connect(self._training_started)
        self.training_view.trainingFinished.connect(self._training_finished)
        self.training_view.modelCreated.connect(self._model_created)
        self.training_view.statusMessage.connect(self.statusBar().showMessage)

        self._refresh_dataset_status()
        self._apply_window_mode()
        self.detection_view.start()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Lägen")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)

        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)

        self.detection_action = QAction("Detektion", self)
        self.detection_action.setCheckable(True)
        self.detection_action.setChecked(True)
        self.detection_action.triggered.connect(lambda: self._show_mode(0))
        self.mode_group.addAction(self.detection_action)
        toolbar.addAction(self.detection_action)

        self.training_action = QAction("Träning", self)
        self.training_action.setCheckable(True)
        self.training_action.triggered.connect(lambda: self._show_mode(2))
        self.mode_group.addAction(self.training_action)
        toolbar.addAction(self.training_action)

        self.annotation_action = QAction("Annotering", self)
        self.annotation_action.setEnabled(False)
        toolbar.addAction(self.annotation_action)

        toolbar.addSeparator()
        export_action = QAction("Exportera dataset...", self)
        export_action.triggered.connect(self._export_dataset)
        toolbar.addAction(export_action)

        settings_action = QAction("Inställningar...", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        self.fullscreen_action = QAction("Fullscreen", self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setShortcut(QKeySequence("F11"))
        self.fullscreen_action.triggered.connect(self._toggle_fullscreen)
        toolbar.addAction(self.fullscreen_action)

    def _show_mode(self, index: int) -> None:
        if index == 0:
            self.detection_action.setChecked(True)
            self.annotation_action.setEnabled(False)
        elif index == 2:
            self.training_action.setChecked(True)
        self.stack.setCurrentIndex(index)

    def _open_annotation(self, capture: PendingCapture) -> None:
        try:
            _, metadata = self.store.load()
        except Exception:
            metadata = None
        classes = metadata.categories if metadata else []
        self.annotation_view.load_capture(capture, classes)
        self.annotation_action.setEnabled(True)
        self.mode_group.setExclusive(False)
        self.detection_action.setChecked(False)
        self.training_action.setChecked(False)
        self.mode_group.setExclusive(True)
        self.stack.setCurrentWidget(self.annotation_view)
        self.statusBar().showMessage(f"Annotera bildpar {capture.group_id}")

    def _annotation_saved(self, message: str) -> None:
        self._refresh_dataset_status()
        self.annotation_action.setEnabled(False)
        self._show_mode(0)
        self.statusBar().showMessage(message, 10000)

    def _annotation_cancelled(self) -> None:
        self.annotation_action.setEnabled(False)
        self._show_mode(0)
        self.statusBar().showMessage("Annoteringen avbröts.", 5000)

    def _training_started(self) -> None:
        self.detection_view.pause_inference(True)
        self._refresh_dataset_status()

    def _training_finished(self, success: bool, message: str) -> None:
        self.detection_view.pause_inference(False)
        self._refresh_dataset_status()
        if success:
            self.statusBar().showMessage(message, 15000)

    def _model_created(self, weights: str) -> None:
        LOGGER.info("Ny modell skapad: %s", weights)

    def _export_dataset(self) -> None:
        try:
            _, metadata = self.store.load()
        except Exception as exc:
            QMessageBox.warning(self, "Export", f"Kunde inte läsa datasetet: {exc}")
            return
        dialog = ExportDialog(metadata, self.paths.exports, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        directory, formats, archive = dialog.values()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = export_dataset(
                self.store,
                directory,
                formats=formats,
                freeze_version=True,
                create_archive=archive,
            )
        except Exception as exc:
            LOGGER.exception("Export misslyckades")
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Export", f"Exporten misslyckades:\n{exc}")
            return
        finally:
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
        self._refresh_dataset_status()
        manifest = result.manifest
        text = (
            f"Export klar: {result.directory}\n\n"
            f"Version: {manifest['version']}\n"
            f"Bilder: {manifest['image_count']}\n"
            f"Annotationer: {manifest['annotation_count']}\n"
            f"Klasser: {manifest['category_count']}"
        )
        if result.archive is not None:
            text += f"\nArkiv: {result.archive}"
        QMessageBox.information(self, "Export klar", text)
        self.statusBar().showMessage(f"Dataset exporterat till {result.directory}", 10000)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.config = dialog.updated_config()
        try:
            save_config(self.config)
        except Exception as exc:
            LOGGER.exception("Kunde inte spara konfiguration")
            QMessageBox.warning(
                self,
                "Inställningar",
                f"Inställningarna används men kunde inte sparas: {exc}",
            )
        self.detection_view.apply_config(self.config)
        self.training_view.apply_config(self.config)
        self._apply_window_mode()
        self.statusBar().showMessage("Inställningar uppdaterade.", 5000)

    def _refresh_dataset_status(self) -> None:
        try:
            _, metadata = self.store.load()
            text = (
                f"Dataset: {metadata.dataset_id} v{metadata.version} · "
                f"{metadata.image_count} bilder · {metadata.annotation_count} annotationer"
            )
            self.setWindowTitle(f"X-ray detector – {metadata.dataset_id} v{metadata.version}")
        except Exception:
            text = "Dataset: –"
        self.dataset_status.setText(text)

    def _toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()
        self.config.app.fullscreen = checked
        self._apply_cursor()

    def _apply_window_mode(self) -> None:
        if self.config.app.fullscreen or self.config.app.kiosk:
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)
        self._apply_cursor()

    def _apply_cursor(self) -> None:
        if self.config.app.kiosk or self.config.app.hide_cursor:
            self.setCursor(Qt.CursorShape.BlankCursor)
        else:
            self.unsetCursor()

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen() and not self.config.app.kiosk:
            self.showNormal()
            self.fullscreen_action.setChecked(False)
            self.config.app.fullscreen = False
            self._apply_cursor()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        try:
            self.training_view.shutdown()
            self.detection_view.stop()
        finally:
            super().closeEvent(event)
