from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config import AppConfig
from src.core.models_schema import CapturedFramePair, TrainedModelInfo, TrainingConfig
from src.core.scheduler import TrainingScheduler
from src.dataset.dataset_manager import DatasetManager
from src.ml.inference_worker import InferenceWorker
from src.ml.model_registry import ModelRegistry
from src.ml.training_worker import TrainingWorker
from src.ui.annotation_view import AnnotationView
from src.ui.detection_view import DetectionView
from src.ui.training_view import TrainingView
from src.video.stream_manager import StreamManager


class ActivityFilter(QObject):
    """Fångar upp användaraktivitet (mus/tangentbord) för att nollställa inaktivitetstimern."""

    def __init__(self, scheduler: TrainingScheduler, parent=None) -> None:
        super().__init__(parent)
        self.scheduler = scheduler

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
        ):
            self.scheduler.record_user_activity()
        return super().eventFilter(obj, event)


class MainWindow(QMainWindow):
    """Huvudfönster med stöd för kioskläge (fullscreen) och växling mellan Detektion, Annotering och Träning."""

    MODE_DETECTION = 0
    MODE_ANNOTATION = 1
    MODE_TRAINING = 2

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.setWindowTitle(str(self.config.app.get("title", "X-ray Detector")))
        self.resize(1480, 880)
        self.setStyleSheet("QMainWindow { background-color: #0b0f14; color: #f8fafc; }")

        # 1. Initiera kärntjänster
        self.dataset_manager = DatasetManager(
            working_dir=self.config.dataset.get("working_dir", "data/working"),
            exports_dir=self.config.dataset.get("exports_dir", "data/datasets"),
            default_classes=self.config.dataset.get("default_classes"),
        )
        self.model_registry = ModelRegistry(
            models_dir=self.config.models.get("models_dir", "models/trained"),
            base_models=self.config.get_base_models(),
        )
        self.stream_manager = StreamManager(self.config.cameras, self)
        self.inference_worker = InferenceWorker(
            stream_manager=self.stream_manager,
            model_family=str(self.config.detection.get("active_model_family", "YOLO26")),
            weights_path=str(self.config.detection.get("active_weights_path", "")),
            confidence_threshold=float(self.config.detection.get("confidence_threshold", 0.25)),
            iou_threshold=float(self.config.detection.get("iou_threshold", 0.45)),
            target_fps=int(self.config.detection.get("target_fps", 30)),
        )
        self.scheduler = TrainingScheduler(
            inactivity_timeout_minutes=int(self.config.app.get("inactivity_timeout_minutes", 30)),
            night_start_str=str(self.config.app.get("night_training_window_start", "23:00")),
            night_end_str=str(self.config.app.get("night_training_window_end", "05:00")),
            parent=self,
        )
        self._training_worker: Optional[TrainingWorker] = None
        self._activity_filter = ActivityFilter(self.scheduler, self)

        # 2. Bygg UI
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Topp-navigationsrad
        top_bar = QFrame()
        top_bar.setFixedHeight(58)
        top_bar.setStyleSheet(
            "QFrame { background-color: #131a24; border-bottom: 1px solid #263244; }"
        )
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 6, 16, 6)
        top_layout.setSpacing(10)

        brand_lbl = QLabel("⚡ X-RAY DETECTOR")
        brand_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #38bdf8; letter-spacing: 1px; border: none;"
        )

        self.btn_mode_detection = self._create_nav_button("1. Detektionsläge", True)
        self.btn_mode_annotation = self._create_nav_button("2. Annoteringsläge", False)
        self.btn_mode_training = self._create_nav_button("3. Träningsläge", False)

        self.btn_mode_detection.clicked.connect(lambda: self.switch_mode(self.MODE_DETECTION))
        self.btn_mode_annotation.clicked.connect(lambda: self.switch_mode(self.MODE_ANNOTATION))
        self.btn_mode_training.clicked.connect(lambda: self.switch_mode(self.MODE_TRAINING))

        self.status_indicator = QLabel("Initierar kameraströmmar...")
        self.status_indicator.setStyleSheet("color: #94a3b8; font-size: 12px; border: none;")

        self.fullscreen_btn = QPushButton("⛶ Fullskärm / Kioskläge (F11)")
        self.fullscreen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fullscreen_btn.setStyleSheet(
            "background-color: #1e293b; color: #e2e8f0; padding: 7px 14px; border: 1px solid #334155; border-radius: 6px; font-weight: bold;"
        )
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen_kiosk)

        top_layout.addWidget(brand_lbl)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.btn_mode_detection)
        top_layout.addWidget(self.btn_mode_annotation)
        top_layout.addWidget(self.btn_mode_training)
        top_layout.addStretch()
        top_layout.addWidget(self.status_indicator)
        top_layout.addSpacing(10)
        top_layout.addWidget(self.fullscreen_btn)

        # Vyer i QStackedWidget
        self.stack = QStackedWidget()
        self.detection_view = DetectionView(self)
        self.annotation_view = AnnotationView(self.dataset_manager, self)
        self.training_view = TrainingView(self.dataset_manager, self.model_registry, self)

        self.stack.addWidget(self.detection_view)
        self.stack.addWidget(self.annotation_view)
        self.stack.addWidget(self.training_view)

        root_layout.addWidget(top_bar)
        root_layout.addWidget(self.stack, stretch=1)

        # 3. Koppla signaler mellan vyer och arbetstrådar
        self.detection_view.populate_models(
            self.model_registry.list_all_selectable_detectors(),
            active_weights=str(self.config.detection.get("active_weights_path", "")),
        )
        self.detection_view.capture_requested.connect(self._on_capture_from_detection)
        self.detection_view.model_selection_changed.connect(self._on_detector_model_changed)
        self.detection_view.confidence_changed.connect(self.inference_worker.set_confidence_threshold)

        self.annotation_view.saved_and_return.connect(self._on_annotation_saved_or_closed)
        self.annotation_view.dataset_exported.connect(lambda _: self.training_view.refresh_datasets_and_models())

        self.training_view.start_training_requested.connect(self.start_training_job)
        self.training_view.stop_training_requested.connect(self.stop_training_job)
        self.training_view.schedule_training_requested.connect(self.scheduler.queue_job)
        self.training_view.export_dataset_requested.connect(self._on_export_from_training_view)

        self.scheduler.status_updated.connect(self.training_view.schedule_status_label.setText)
        self.scheduler.trigger_scheduled_training.connect(self.start_training_job)

        self.stream_manager.camera_status_changed.connect(self._on_camera_status)
        self.inference_worker.frames_processed.connect(self.detection_view.update_frames)
        self.inference_worker.status_changed.connect(self.status_indicator.setText)

        # 4. Starta videoströmmar och inferenstråd
        self.stream_manager.start_streams()
        self.inference_worker.start()

        # Starta i kioskläge/fullskärm om inställt i config.yaml
        if bool(self.config.app.get("kiosk_fullscreen", False)):
            self.showFullScreen()

    @staticmethod
    def _create_nav_button(text: str, active: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setChecked(active)
        MainWindow._style_nav_button(btn, active)
        return btn

    @staticmethod
    def _style_nav_button(btn: QPushButton, active: bool) -> None:
        if active:
            btn.setStyleSheet(
                "background-color: #2563eb; color: #ffffff; font-weight: bold; font-size: 14px; padding: 8px 18px; border-radius: 6px; border: 1px solid #3b82f6;"
            )
        else:
            btn.setStyleSheet(
                "background-color: #1e293b; color: #cbd5e1; font-size: 14px; padding: 8px 18px; border-radius: 6px; border: 1px solid #334155;"
            )

    def switch_mode(self, mode_index: int) -> None:
        self.stack.setCurrentIndex(mode_index)
        buttons = [self.btn_mode_detection, self.btn_mode_annotation, self.btn_mode_training]
        for idx, btn in enumerate(buttons):
            is_act = idx == mode_index
            btn.setChecked(is_act)
            self._style_nav_button(btn, is_act)

        if mode_index == self.MODE_ANNOTATION:
            self.annotation_view.refresh_classes_and_stats()
        elif mode_index == self.MODE_TRAINING:
            self.training_view.refresh_datasets_and_models()

    def _on_capture_from_detection(self, pair: CapturedFramePair) -> None:
        """Laddar de två frysta bilderna och befintliga detektioner i annoteringsläget och byter vy."""
        self.annotation_view.load_captured_pair(pair)
        self.switch_mode(self.MODE_ANNOTATION)

    def _on_annotation_saved_or_closed(self) -> None:
        self.training_view.refresh_datasets_and_models()
        self.switch_mode(self.MODE_DETECTION)

    def _on_detector_model_changed(self, family: str, weights_path: str) -> None:
        conf = float(self.detection_view.conf_slider.value()) / 100.0
        self.inference_worker.switch_model(
            model_family=family,
            weights_path=weights_path,
            confidence_threshold=conf,
        )

    def _on_export_from_training_view(self, export_format: str) -> None:
        info = self.dataset_manager.export_new_version(export_format=export_format)
        self.training_view.refresh_datasets_and_models()
        self.annotation_view.refresh_classes_and_stats()
        self.status_indicator.setText(
            f"Exporterade Dataset v{info.version} ({info.num_images} bilder, {info.num_objects} objekt)"
        )

    def start_training_job(self, config: TrainingConfig) -> None:
        if self._training_worker is not None and self._training_worker.isRunning():
            return

        # Pausa detektion under träning om valt för att maximera tillgängliga hårdvaruresurser
        if config.pause_detection_during_training:
            self.inference_worker.set_paused(True)
            self.detection_view.set_detection_paused_state(True)

        self.training_view.set_training_running_state(True)
        self._training_worker = TrainingWorker(
            config=config,
            models_dir=self.config.models.get("models_dir", "models/trained"),
        )
        self._training_worker.progress_updated.connect(self.training_view.on_training_progress)
        self._training_worker.training_completed.connect(self._on_training_finished)
        self._training_worker.training_failed.connect(self._on_training_failed)
        self._training_worker.start()

    def stop_training_job(self) -> None:
        if self._training_worker is not None and self._training_worker.isRunning():
            self._training_worker.request_stop()

    def _on_training_finished(self, info: TrainedModelInfo) -> None:
        # Återuppta detektion och uppdatera modellistan med den nya modellen (med datasetets versionssiffra)
        self.inference_worker.set_paused(False)
        self.detection_view.set_detection_paused_state(False)
        self.detection_view.populate_models(
            self.model_registry.list_all_selectable_detectors(),
            active_weights=info.weights_path,
        )
        self._on_detector_model_changed(info.model_family, info.weights_path)
        self.training_view.on_training_completed(info)

    def _on_training_failed(self, error_msg: str) -> None:
        self.inference_worker.set_paused(False)
        self.detection_view.set_detection_paused_state(False)
        self.training_view.on_training_failed(error_msg)

    def _on_camera_status(self, stream_id: int, msg: str, is_hw: bool) -> None:
        self.status_indicator.setText(msg)

    def toggle_fullscreen_kiosk(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("⛶ Fullskärm / Kioskläge (F11)")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("🗗 Avsluta Fullskärm (F11 / Esc)")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen_kiosk()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen_kiosk()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space and self.stack.currentIndex() == self.MODE_DETECTION:
            self.detection_view.trigger_capture()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        if self._training_worker is not None and self._training_worker.isRunning():
            self._training_worker.request_stop()
            self._training_worker.wait(2000)
        self.inference_worker.stop()
        self.stream_manager.stop_streams()
        super().closeEvent(event)
