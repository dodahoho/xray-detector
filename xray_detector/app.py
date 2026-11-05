"""MainWindow – orkestrerar lägen, capture, inferens, dataset och träning."""
from __future__ import annotations

import numpy as np
from loguru import logger
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from xray_detector.annotation.annotation_view import AnnotationView
from xray_detector.capture.capture_worker import CaptureWorker
from xray_detector.config import Config
from xray_detector.dataset.dataset_manager import DatasetManager
from xray_detector.dataset.yolo_export import export_yolo
from xray_detector.detection.inference_worker import InferenceWorker
from xray_detector.detection.model_registry import (
    BaseModel,
    Detection,
    create_model,
    resolve_device,
)
from xray_detector.training.trainer import TrainingWorker
from xray_detector.training.training_view import TrainingView
from xray_detector.ui.dataset_dialog import DatasetDialog
from xray_detector.ui.detection_view import DetectionView


class MainWindow(QMainWindow):
    """Huvudfönstret med tre lägen."""

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setWindowTitle("X-ray Detector")
        self.resize(1600, 900)

        # State
        self._latest_frames: dict[int, np.ndarray] = {}
        self._latest_dets: dict[int, list[Detection]] = {}
        self._capture_workers: list[CaptureWorker] = []
        self._inference: InferenceWorker | None = None
        self._training_worker: TrainingWorker | None = None
        self._training_active = False
        self._dataset_version: str | None = None
        self._stream_errors: set[int] = set()
        self._stream_ready: set[int] = set()

        # Dataset
        self.dataset_manager = DatasetManager(config.dataset_root)

        # UI
        self._build_ui()

        # Timer för att uppdatera detektionsvyn
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(30)
        self._ui_timer.timeout.connect(self._update_detection_view)
        self._ui_timer.start()

        # Starta capture + inferens
        self._start_detection()

        # Fullscreen om konfigurerat
        if config.app.fullscreen:
            self.showFullScreen()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Topplista
        top = QHBoxLayout()
        top.setContentsMargins(8, 6, 8, 6)
        self.mode_label = QLabel("Läge: Detektion")
        self.mode_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top.addWidget(self.mode_label)
        top.addStretch(1)

        self.dataset_btn = QPushButton("Dataset...")
        self.dataset_btn.clicked.connect(self._open_dataset_dialog)
        top.addWidget(self.dataset_btn)

        self.models_btn = QPushButton("Modeller...")
        self.models_btn.clicked.connect(self._open_model_dialog)
        top.addWidget(self.models_btn)

        self.fullscreen_btn = QPushButton("Fullscreen (F11)")
        self.fullscreen_btn.setCheckable(True)
        self.fullscreen_btn.setChecked(self.isFullScreen())
        self.fullscreen_btn.toggled.connect(self._toggle_fullscreen)
        top.addWidget(self.fullscreen_btn)
        root.addLayout(top)

        # Stacked widget med de tre lägena
        self.stack = QStackedWidget()
        self.detection_view = DetectionView()
        self.detection_view.capture_requested.connect(self._on_capture)
        self.detection_view.stream_retry_requested.connect(self._on_retry_stream)
        self.stack.addWidget(self.detection_view)  # index 0

        self.annotation_view = AnnotationView(self.config.classes)
        self.annotation_view.saved.connect(self._on_annotation_saved)
        self.annotation_view.cancelled.connect(self._on_annotation_cancelled)
        self.stack.addWidget(self.annotation_view)  # index 1

        self.training_view = self._build_training_view()
        self.stack.addWidget(self.training_view)  # index 2

        root.addWidget(self.stack, stretch=1)

        # Statusrad
        self.status_label = QLabel("Startar...")
        self.status_label.setStyleSheet("padding: 4px 8px; background: #222; color: #ccc;")
        root.addWidget(self.status_label)

        # Tangentbordskommandon
        self._add_shortcuts()

        self._set_mode(0)

    def _build_training_view(self) -> TrainingView:
        models = self._list_models()
        datasets = [
            {"version": v, **self.dataset_manager.metadata(v)}
            for v in self.dataset_manager.list_versions()
        ]
        defaults = {
            "epochs": self.config.training.default_epochs,
            "imgsz": self.config.training.default_imgsz,
            "batch": self.config.training.default_batch,
            "device": self.config.detection.device,
        }
        tv = TrainingView(models, datasets, defaults)
        tv.start_requested.connect(self._on_training_start)
        return tv

    def _add_shortcuts(self) -> None:
        act_fs = QAction("Fullscreen", self)
        act_fs.setShortcut(QKeySequence("F11"))
        act_fs.triggered.connect(self._toggle_fullscreen)
        self.addAction(act_fs)

        act_det = QAction("Detektionsläge", self)
        act_det.setShortcut(QKeySequence("1"))
        act_det.triggered.connect(lambda: self._set_mode(0))
        self.addAction(act_det)

        act_train = QAction("Träningsläge", self)
        act_train.setShortcut(QKeySequence("3"))
        act_train.triggered.connect(lambda: self._set_mode(2))
        self.addAction(act_train)

    def keyPressEvent(self, event) -> None:
        """Fånga med F – endast i detektionsläget.

        Hanteras här i stället för som QAction så att F kan skrivas som
        vanlig text i annoteringens textfält (t.ex. nya klassnamn).
        """
        if event.key() == Qt.Key_F and self.stack.currentWidget() is self.detection_view:
            self._on_capture()
            event.accept()
            return
        super().keyPressEvent(event)

    def _set_mode(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        names = {0: "Detektion", 1: "Annotering", 2: "Träning"}
        self.mode_label.setText(f"Läge: {names.get(index, '?')}")

    def _toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    # ------------------------------------------------------- Capture/Inferens
    def _start_detection(self) -> None:
        """Starta capture- och inference-threads."""
        self.status_label.setText("Startar videoströmmar...")
        det = self.config.detection
        device = resolve_device(det.device)
        if device == "cpu":
            logger.warning(
                "CUDA är inte tillgänglig – inferens körs på CPU (config device={})",
                det.device,
            )
        else:
            logger.info("Använder GPU {} för inferens", device)

        # Skapa modeller per stream
        models: dict[int, BaseModel] = {}
        try:
            models[0] = create_model(det.model_left, device, det.quantize)
            models[1] = create_model(det.model_right, device, det.quantize)
        except Exception as e:  # noqa: BLE001
            logger.exception("Kunde inte skapa modeller")
            QMessageBox.critical(self, "Modellfel", f"Kunde inte ladda modeller:\n{e}")
            return

        # Capture-threads
        for i in range(len(self.config.capture.streams)):
            self._start_capture_stream(i)

        # Inference-thread
        self._inference = InferenceWorker(models, conf=det.conf, iou=det.iou)
        self._inference.detections_ready.connect(self._on_detections)
        self._inference.error.connect(self._on_inference_error)
        self._inference.start()

        self.status_label.setText(
            f"Detektion aktiv | {det.model_left} | {det.model_right} | "
            f"conf={det.conf} device={device} quantize={det.quantize}"
        )

    def _start_capture_stream(self, index: int) -> None:
        """Starta en capture-worker för en enskild ström."""
        cw = CaptureWorker(
            index=index,
            stream=self.config.capture.streams[index],
            backend=self.config.capture.backend,
            preprocess_mode=self.config.detection.preprocess,
        )
        cw.frame_ready.connect(self._on_frame)
        cw.connecting.connect(self._on_capture_connecting)
        cw.error.connect(self._on_capture_error)
        cw.start()
        self._capture_workers.append(cw)

    def _on_retry_stream(self, index: int) -> None:
        """Starta om en ström manuellt när användaren trycker 'Försök igen'."""
        if index < 0 or index >= len(self.config.capture.streams):
            return
        # Stoppa och ta bort eventuell tidigare worker för strömmen.
        for cw in list(self._capture_workers):
            if cw.index != index:
                continue
            if cw.isRunning():
                cw.stop()
            self._capture_workers.remove(cw)

        self._stream_errors.discard(index)
        self._stream_ready.discard(index)
        self._latest_frames.pop(index, None)
        self._latest_dets.pop(index, None)
        self.detection_view.set_stream_connecting(index)
        self.status_label.setText(f"Försöker ansluta videokälla (stream {index})...")
        self._start_capture_stream(index)

    def _on_frame(self, index: int, frame: np.ndarray) -> None:
        was_ready = index in self._stream_ready
        self._stream_ready.add(index)
        self._latest_frames[index] = frame
        if index in self._stream_errors:
            self._stream_errors.discard(index)
            logger.info("Video återupptagen på stream {}", index)
        if not was_ready:
            self.detection_view.set_stream_ok(index)
            if len(self._stream_ready) >= len(self.config.capture.streams):
                self.status_label.setText(
                    "Detektion aktiv – alla videokällor anslutna"
                )
            else:
                self.status_label.setText(f"Video ansluten (stream {index})")
        # Skicka frame till inference-workern (nyaste vinner, drop-oldest)
        if self._inference is not None:
            self._inference.push_frame(index, frame)

    def _on_detections(self, index: int, dets: list[Detection]) -> None:
        self._latest_dets[index] = dets

    def _on_capture_connecting(
        self, index: int, attempt: int, max_attempts: int
    ) -> None:
        self._stream_ready.discard(index)
        self.detection_view.set_stream_connecting(index, attempt, max_attempts)
        self.status_label.setText(
            f"Ansluter videokälla (stream {index}), försök "
            f"{attempt}/{max_attempts}..."
        )

    def _on_capture_error(self, index: int, msg: str) -> None:
        logger.error("Capture fel stream {}: {}", index, msg)
        self._stream_errors.add(index)
        self._stream_ready.discard(index)
        # Töm gamla frames så att inte en frusen bild visas som "live"
        self._latest_frames.pop(index, None)
        self._latest_dets.pop(index, None)
        self.detection_view.set_stream_error(index, "Ingen videokälla")
        self.status_label.setText(
            f"Ingen videokälla (stream {index}): {msg} – "
            f"använd 'Försök igen' i videofönstret"
        )

    def _on_inference_error(self, index: int, msg: str) -> None:
        logger.error("Inferens fel stream {}: {}", index, msg)
        self.status_label.setText(f"Detekteringsfel (stream {index}): {msg}")

    def _update_detection_view(self) -> None:
        """Kopplas till timer – uppdatera detektionsvyn med nyaste data."""
        if self.stack.currentWidget() is not self.detection_view:
            return
        f0 = self._latest_frames.get(0)
        f1 = self._latest_frames.get(1)
        d0 = self._latest_dets.get(0, [])
        d1 = self._latest_dets.get(1, [])
        if f0 is not None:
            self.detection_view.set_left(f0, d0)
        if f1 is not None:
            self.detection_view.set_right(f1, d1)

    # ------------------------------------------------------------- Fångning
    def _on_capture(self) -> None:
        # Endast från detektionsläget (F-kortkommandot är visserligen bundet
        # till detektionsvyn, men knappen kan även trigga via andra vägar).
        if self.stack.currentWidget() is not self.detection_view:
            return
        f0 = self._latest_frames.get(0)
        f1 = self._latest_frames.get(1)
        if f0 is None and f1 is None:
            QMessageBox.warning(self, "Fånga", "Ingen video ännu – vänta på strömmarna")
            return
        d0 = self._latest_dets.get(0, [])
        d1 = self._latest_dets.get(1, [])
        self.annotation_view.set_images(f0, f1, d0, d1)
        self._set_mode(1)
        self.status_label.setText("Annotering – rita rektanglar, välj klass, spara")

    def _on_annotation_saved(self) -> None:
        left_img = self.annotation_view.left_image
        right_img = self.annotation_view.right_image
        left_anns = self.annotation_view.left_annotations
        right_anns = self.annotation_view.right_annotations

        # Spara de strömmar som faktiskt har en bild. Med bara ett UVC-kort
        # saknas den andra strömmen och ska inte blockera annoteringen.
        images: list[np.ndarray] = []
        annotations: list[list[dict]] = []
        if left_img is not None:
            images.append(left_img)
            annotations.append(left_anns)
        if right_img is not None:
            images.append(right_img)
            annotations.append(right_anns)

        if not images:
            self._set_mode(0)
            self.status_label.setText("Annotering klar – inga bilder att spara")
            return

        # Säkerställ att en datasetversion finns
        if self._dataset_version is None:
            v = self.dataset_manager.next_version()
            self.dataset_manager.create_version(categories=self.config.classes)
            self._dataset_version = v
            logger.info("Skapade datasetversion {}", v)

        added = self.dataset_manager.add_images(
            self._dataset_version,
            images,
            annotations,
            source="capture",
        )
        num_objects = sum(len(a) for a in annotations)
        self.status_label.setText(
            f"Sparade {added} bilder i {self._dataset_version} "
            f"({num_objects} objekt)"
        )
        self._set_mode(0)

    def _on_annotation_cancelled(self) -> None:
        self._set_mode(0)
        self.status_label.setText("Annotering avbruten")

    # ------------------------------------------------------------- Dataset
    def _open_dataset_dialog(self) -> None:
        dlg = DatasetDialog(self.dataset_manager, self)
        dlg.exec()
        # Uppdatera träningsvyns dataset-lista
        self._refresh_training_datasets()

    def _refresh_training_datasets(self) -> None:
        datasets = [
            {"version": v, **self.dataset_manager.metadata(v)}
            for v in self.dataset_manager.list_versions()
        ]
        # Återuppbygga dataset-combobox i training view
        combo = self.training_view.dataset_combo
        combo.blockSignals(True)
        combo.clear()
        for d in datasets:
            label = (
                f"{d['version']}  ({d.get('num_images', 0)} bilder, "
                f"{d.get('num_objects', 0)} objekt)"
            )
            combo.addItem(label, d["version"])
        if not datasets:
            combo.addItem("(inga dataset – annotera först)")
        combo.blockSignals(False)

    # ------------------------------------------------------------- Modeller
    def _list_models(self) -> list[str]:
        """Lista tillgängliga .pt-modeller i models/ + defaults."""
        models_dir = self.config.models_dir
        found: list[str] = []
        if models_dir.exists():
            found = [
                str(p) for p in sorted(models_dir.glob("*.pt"))
            ]
        # Säkerställ att några defaults finns (ultralytics kan ladda dem)
        defaults = ["yolo26n.pt", "yolo26s.pt", "yolo26l.pt", "rfdetr-l.pt"]
        for d in defaults:
            if d not in found:
                found.append(d)
        return found

    def _open_model_dialog(self) -> None:
        """Välj modell per stream (enkel dialog)."""
        models = self._list_models()
        from PySide6.QtWidgets import QInputDialog
        left, ok = QInputDialog.getItem(
            self, "Vänster modell", "Välj modell (vänster ström):", models, 0, False
        )
        if ok:
            self.config.detection.model_left = left
        right, ok = QInputDialog.getItem(
            self, "Höger modell", "Välj modell (höger ström):", models, 0, False
        )
        if ok:
            self.config.detection.model_right = right
        # Återstarta inferens med nya modeller
        self._restart_inference()
        self.status_label.setText(f"Modeller: {left} | {right}")

    def _restart_inference(self) -> None:
        if self._inference is not None:
            self._inference.stop()
        det = self.config.detection
        device = resolve_device(det.device)
        models: dict[int, BaseModel] = {}
        try:
            models[0] = create_model(det.model_left, device, det.quantize)
            models[1] = create_model(det.model_right, device, det.quantize)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Modellfel", str(e))
            return
        self._inference = InferenceWorker(models, conf=det.conf, iou=det.iou)
        self._inference.detections_ready.connect(self._on_detections)
        self._inference.error.connect(self._on_inference_error)
        self._inference.start()

    # ------------------------------------------------------------- Träning
    def _on_training_start(
        self, model_path: str, ds_version: str,
        epochs: int, imgsz: int, batch: int, device: int,
    ) -> None:
        if self._training_active:
            return
        device = resolve_device(device)
        # Exportera dataset till YOLO
        ds = self.dataset_manager.open(ds_version)
        if not ds.images:
            QMessageBox.warning(self, "Träning", f"Dataset {ds_version} har inga bilder")
            return
        yolo_dir = export_yolo(ds)
        data_yaml = str(yolo_dir / "data.yaml")

        # Pausa detektion
        self._training_active = True
        if self._inference is not None:
            self._inference.set_paused(True)
        self.training_view.set_running(True)
        self.status_label.setText(f"Träning pågår ({ds_version}) – detektion pausad")

        # Skapa worker
        project_dir = self.config.runs_dir / ds_version
        self._training_worker = TrainingWorker(
            base_model_path=model_path,
            data_yaml=data_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            project_dir=project_dir,
        )
        self._training_worker.log.connect(self.training_view.append_log)
        self._training_worker.progress.connect(self.training_view.set_progress)
        self._training_worker.finished_ok.connect(self._on_training_done)
        self._training_worker.failed.connect(self._on_training_failed)
        self._training_worker.start()

    def _on_training_done(self, path: str) -> None:
        self._training_active = False
        if self._inference is not None:
            self._inference.set_paused(False)
        self.training_view.set_finished(path)
        self.status_label.setText("Träning klar – detektion återupptagen")
        # Uppdatera modell-lista
        self._refresh_training_datasets()

    def _on_training_failed(self, msg: str) -> None:
        self._training_active = False
        if self._inference is not None:
            self._inference.set_paused(False)
        self.training_view.set_failed(msg)
        self.status_label.setText("Träning misslyckades – detektion återupptagen")

    # ------------------------------------------------------------- Stängning
    def closeEvent(self, event) -> None:
        logger.info("Stänger applikationen...")
        self._ui_timer.stop()
        if self._inference is not None:
            self._inference.stop()
        for cw in self._capture_workers:
            cw.stop()
        if self._training_worker is not None and self._training_worker.isRunning():
            self._training_worker.stop()
            self._training_worker.wait(2000)
        event.accept()
