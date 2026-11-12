import logging

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStatusBar, QTabWidget

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.config import AppConfig
from xray_detector.ui.annotation_view import AnnotationView
from xray_detector.ui.dataset_view import DatasetView
from xray_detector.ui.detection_view import DetectionView
from xray_detector.ui.settings_view import SettingsView
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.theme import apply_theme
from xray_detector.ui.training_view import TrainingView


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("X-ray detector")
        self.dataset_service = DatasetService(config.dataset_dir)
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
        apply_theme(
            QApplication.instance(),
            self.settings.value("ui/theme", "system", type=str),
        )

        self.detection_view = DetectionView(config, self.settings)
        # annoteringsvyns standardklasser är vald modells klasser (TASK-61)
        self.annotation_view = AnnotationView(
            config,
            self.dataset_service,
            self.settings,
            model_classes=self.detection_view.model_class_names,
        )
        self.dataset_view = DatasetView(config, self.dataset_service, self.settings)
        self.training_view = TrainingView(config, self.dataset_service, self.settings)
        self.settings_view = SettingsView(self.settings)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.detection_view, mnemonic("Detektion", "D"))
        self.tabs.addTab(self.annotation_view, mnemonic("Annotation", "A"))
        self.tabs.addTab(self.dataset_view, mnemonic("Dataset", "S"))
        self.tabs.addTab(self.training_view, mnemonic("Träning", "T"))
        self.tabs.addTab(self.settings_view, mnemonic("Inställningar", "L"))
        self.tabs.setTabEnabled(1, False)
        self._tab_guard = False
        # fliken annoteringen öppnades från, dit Spara och Avbryt återgår (TASK-60)
        self._annotation_origin = 0
        self.tabs.currentChanged.connect(self._on_tab_changed)
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
        self.dataset_view.open_annotation_requested.connect(self._on_open_from_dataset)
        self.dataset_view.status_changed.connect(self._show_status)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("Klar")
        self.status.addWidget(self.status_label)

        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

        self.detection_view.check_device()

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

    def _confirm_unsaved(self) -> str:
        """Frågar om osparade annoteringar; returnerar 'save'/'discard'/'cancel'."""
        from PySide6.QtWidgets import QMessageBox

        answer = QMessageBox.question(
            self,
            "Osparade annoteringar",
            "Det finns osparade annoteringar. Spara dem?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return "save"
        if answer == QMessageBox.StandardButton.Discard:
            return "discard"
        return "cancel"

    def _on_tab_changed(self, index: int) -> None:
        if self._tab_guard or index == 1:
            return
        if not (self.tabs.isTabEnabled(1) and self.annotation_view.is_dirty()):
            return
        choice = self._confirm_unsaved()
        if choice == "save":
            self.annotation_view._on_save()
        elif choice == "discard":
            self.annotation_view.mark_clean()
        else:
            self._tab_guard = True
            self.tabs.setCurrentIndex(1)
            self._tab_guard = False

    def _show_status(self, message: str) -> None:
        self.status_label.setText(message)
        logging.getLogger("xray").info("status: %s", message)

    def _on_capture(self, captures) -> None:
        # TASK-12: krascsaker skrivning av fangsten direkt vid knapptryck
        pending_group_id = self.dataset_service.save_pending(captures)
        self._annotation_origin = self.tabs.indexOf(self.detection_view)
        self.annotation_view.load_captures(captures, pending_group_id)
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

    def _on_open_from_dataset(self, payload) -> None:
        # Fran datasetvyn: antingen en ramlisa (sparade bilder) eller en
        # PendingCapture (osparad fangst, TASK-12). Osp rad fangst behaller sitt
        # grupp-id sa ingen ny pending-kopia skrivs vid ateroppning.
        from_pending = hasattr(payload, "frames")
        frames = payload.frames if from_pending else payload
        pending_group_id = getattr(payload, "group_id", None)
        self._annotation_origin = self.tabs.indexOf(self.dataset_view)
        # sparade bilder blir dubbletter om de sparas utan ändring (TASK-62)
        self.annotation_view.load_captures(
            frames, pending_group_id, already_saved=not from_pending
        )
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

    def _on_annotation_saved(self) -> None:
        # sparningen är asynkron (TASK-40): fliken kan redan ha bytts medan den skrevs
        on_annotation_tab = self.tabs.currentIndex() == 1
        self.tabs.setTabEnabled(1, False)
        if on_annotation_tab:
            self.tabs.setCurrentIndex(self._annotation_origin)
        self.training_view.refresh_dataset_info()
        self.dataset_view.refresh()
        self._show_status("Annoteringar sparade till dataset")

    def _on_annotation_cancelled(self) -> None:
        self.tabs.setTabEnabled(1, False)
        self.tabs.setCurrentIndex(self._annotation_origin)

    def _on_training_started(self) -> None:
        self.detection_view.pause_detection()
        self._show_status("Träning pågår – detektion pausad")

    def _on_training_finished(self) -> None:
        self.detection_view.resume_detection()
        self.detection_view.refresh_models()
        self._show_status("Träning avslutad – detektion återupptagen; modellväljaren uppdaterad")

    def closeEvent(self, event) -> None:
        worker = self.training_view.active_worker()
        if worker is not None and worker.is_running():
            from PySide6.QtWidgets import QMessageBox

            answer = QMessageBox.question(
                self,
                "Träning pågår",
                "En träning körs just nu. Avbryta träningen och avsluta?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            worker.cancel()
        if self.tabs.isTabEnabled(1) and self.annotation_view.is_dirty():
            choice = self._confirm_unsaved()
            if choice == "cancel":
                event.ignore()
                return
            if choice == "save":
                self.annotation_view._on_save()
            else:
                self.annotation_view.mark_clean()
        geometry = (self.normalGeometry() if self.isFullScreen() or self.isMaximized() else self.geometry())
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
        # vänta in arbetstrådarna så en pågående skrivning blir klar före avslut (TASK-40)
        self.annotation_view.wait_for_save()
        self.dataset_view.wait_for_refresh()
        self.dataset_view.wait_for_export()
        self.detection_view.stop()
        super().closeEvent(event)
