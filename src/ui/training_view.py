from __future__ import annotations

from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.models_schema import DatasetVersionInfo, TrainedModelInfo, TrainingConfig
from src.dataset.dataset_manager import DatasetManager
from src.ml.model_registry import ModelRegistry


class TrainingView(QWidget):
    """Träningsläge: Val av basmodell, dataset, träningsparametrar, schemaläggning och logg/progress."""

    start_training_requested = Signal(object)  # TrainingConfig
    stop_training_requested = Signal()
    schedule_training_requested = Signal(object)  # TrainingConfig
    cancel_schedule_requested = Signal()
    export_dataset_requested = Signal(str)  # export_format

    def __init__(
        self,
        dataset_manager: DatasetManager,
        model_registry: ModelRegistry,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.dataset_manager = dataset_manager
        self.model_registry = model_registry
        self._datasets: List[DatasetVersionInfo] = []

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(14)

        # Vänster kolumn: Träningskonfiguration & Dataset-översikt
        config_panel = QFrame()
        config_panel.setFixedWidth(470)
        config_panel.setStyleSheet(
            "QFrame { background-color: #18202c; border: 1px solid #2b374b; border-radius: 8px; }"
        )
        cfg_layout = QVBoxLayout(config_panel)
        cfg_layout.setContentsMargins(16, 16, 16, 16)
        cfg_layout.setSpacing(12)

        title = QLabel("Konfigurera Modellträning")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #f8fafc; border: none;")

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # 1. Val av basmodell
        self.base_model_combo = QComboBox()
        self.base_model_combo.setStyleSheet(
            "background-color: #0f141b; color: #f8fafc; padding: 6px; border: 1px solid #3b4b64; border-radius: 5px;"
        )
        for bm in self.model_registry.base_models:
            if bm["family"] != "SIMULATED":
                self.base_model_combo.addItem(f"{bm['name']} [{bm['family']}]", userData=bm)

        # 2. Val av dataset (visar versionssiffra, datum, antal bilder och antal objekt)
        self.dataset_combo = QComboBox()
        self.dataset_combo.setStyleSheet(
            "background-color: #0f141b; color: #f8fafc; padding: 6px; border: 1px solid #3b4b64; border-radius: 5px;"
        )

        # Snabbknapp för att exportera ny datasetversion från working-datasetet direkt härifrån
        ds_export_row = QHBoxLayout()
        self.quick_export_fmt = QComboBox()
        self.quick_export_fmt.addItems(["COCO+YOLO", "COCO", "YOLO"])
        self.quick_export_fmt.setStyleSheet(
            "background-color: #0f141b; color: #f8fafc; padding: 5px; border: 1px solid #3b4b64; border-radius: 5px;"
        )
        self.quick_export_btn = QPushButton("+ Exportera ny dataset-version nu")
        self.quick_export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_export_btn.setStyleSheet(
            "background-color: #0d9488; color: #ffffff; font-weight: bold; padding: 6px 10px; border-radius: 5px;"
        )
        self.quick_export_btn.clicked.connect(
            lambda: self.export_dataset_requested.emit(self.quick_export_fmt.currentText())
        )
        ds_export_row.addWidget(self.quick_export_fmt)
        ds_export_row.addWidget(self.quick_export_btn, stretch=1)

        # 3. Träningsparametrar
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 500)
        self.epochs_spin.setValue(15)
        self.epochs_spin.setStyleSheet("background-color: #0f141b; color: #f8fafc; padding: 5px;")

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 128)
        self.batch_spin.setValue(8)
        self.batch_spin.setStyleSheet("background-color: #0f141b; color: #f8fafc; padding: 5px;")

        self.imgsz_combo = QComboBox()
        self.imgsz_combo.addItems(["640", "800", "1024", "1280"])
        self.imgsz_combo.setCurrentText("640")
        self.imgsz_combo.setStyleSheet("background-color: #0f141b; color: #f8fafc; padding: 5px;")

        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setDecimals(5)
        self.lr_spin.setRange(0.00001, 0.1)
        self.lr_spin.setSingleStep(0.0005)
        self.lr_spin.setValue(0.001)
        self.lr_spin.setStyleSheet("background-color: #0f141b; color: #f8fafc; padding: 5px;")

        # 4. Prestanda & Schemaläggning
        self.schedule_combo = QComboBox()
        self.schedule_combo.addItem("Starta direkt (Manuell start)", userData="immediate")
        self.schedule_combo.addItem("Endast nattetid (Schemalagd natträning)", userData="night")
        self.schedule_combo.addItem("Under inaktivitet (Starta vid inaktivitet)", userData="inactivity")
        self.schedule_combo.setStyleSheet("background-color: #0f141b; color: #f8fafc; padding: 6px;")

        self.pause_detection_cb = QCheckBox(
            "Pausa detektion under träning för att maximera hårdvaruresurser"
        )
        self.pause_detection_cb.setChecked(True)
        self.pause_detection_cb.setStyleSheet("color: #e2e8f0; font-weight: bold;")

        for lbl_text, widget in [
            ("Basmodell:", self.base_model_combo),
            ("Dataset-version:", self.dataset_combo),
            ("Exportera dataset:", ds_export_row),
            ("Antal epoker (Epochs):", self.epochs_spin),
            ("Batch-storlek:", self.batch_spin),
            ("Bildupplösning (px):", self.imgsz_combo),
            ("Learning Rate:", self.lr_spin),
            ("Körläge:", self.schedule_combo),
        ]:
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet("color: #cbd5e1; font-weight: bold; border: none;")
            form.addRow(lbl, widget)

        # Knappar för att starta / avbryta träning
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("🚀  STARTA / SCHEMALÄGG TRÄNING")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setMinimumHeight(46)
        self.start_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #94a3b8;
            }
            """
        )
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.stop_btn = QPushButton("⏹ Avbryt")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setMinimumHeight(46)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "background-color: #991b1b; color: #fecaca; font-weight: bold; padding: 0 16px; border-radius: 7px;"
        )
        self.stop_btn.clicked.connect(self.stop_training_requested.emit)

        btn_row.addWidget(self.start_btn, stretch=1)
        btn_row.addWidget(self.stop_btn)

        self.schedule_status_label = QLabel("Ingen schemalagd träning i kö.")
        self.schedule_status_label.setWordWrap(True)
        self.schedule_status_label.setStyleSheet("color: #38bdf8; font-size: 12px; border: none;")

        cfg_layout.addWidget(title)
        cfg_layout.addLayout(form)
        cfg_layout.addWidget(self.pause_detection_cb)
        cfg_layout.addSpacing(4)
        cfg_layout.addLayout(btn_row)
        cfg_layout.addWidget(self.schedule_status_label)
        cfg_layout.addStretch()

        # Höger kolumn: Progress, Träningslogg & Sparade modellvikter
        right_panel = QFrame()
        right_panel.setStyleSheet(
            "QFrame { background-color: #18202c; border: 1px solid #2b374b; border-radius: 8px; }"
        )
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        prog_title = QLabel("Träningsstatus & Logg")
        prog_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc; border: none;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(26)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #0f141b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 5px;
            }
            """
        )

        self.metrics_label = QLabel("Metriker: Väntar på träningsstart...")
        self.metrics_label.setStyleSheet("color: #2ed573; font-weight: bold; font-size: 13px; border: none;")

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(
            "background-color: #0b0f14; color: #cbd5e1; font-family: Consolas, monospace; font-size: 12px; border: 1px solid #263244; border-radius: 6px;"
        )

        trained_title = QLabel("Sparade Modellvikter (Versionssiffra = Datasetets version)")
        trained_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc; border: none;")

        self.trained_models_list = QListWidget()
        self.trained_models_list.setMaximumHeight(165)
        self.trained_models_list.setStyleSheet(
            "background-color: #0f141b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; font-size: 13px; padding: 4px;"
        )

        right_layout.addWidget(prog_title)
        right_layout.addWidget(self.progress_bar)
        right_layout.addWidget(self.metrics_label)
        right_layout.addWidget(self.log_output, stretch=1)
        right_layout.addWidget(trained_title)
        right_layout.addWidget(self.trained_models_list)

        main_layout.addWidget(config_panel)
        main_layout.addWidget(right_panel, stretch=1)

        self.refresh_datasets_and_models()

    def refresh_datasets_and_models(self) -> None:
        self._datasets = self.dataset_manager.list_exported_versions()
        self.dataset_combo.clear()
        for ds in self._datasets:
            self.dataset_combo.addItem(ds.display_label, userData=ds)

        if not self._datasets:
            num_imgs, num_objs = self.dataset_manager.get_working_stats()
            self.dataset_combo.addItem(
                f"[Auto-export v1 vid start] Aktuellt arbetsdataset ({num_imgs} bilder, {num_objs} objekt)",
                userData=None,
            )

        self.trained_models_list.clear()
        for tm in self.model_registry.list_trained_models():
            map50 = tm.metrics.get("mAP50", 0.0)
            self.trained_models_list.addItem(
                f"v{tm.version}  |  {tm.model_family} ({tm.base_model_name})  |  "
                f"Dataset v{tm.dataset_version}  |  mAP50: {map50:.3f}  |  {tm.weights_path}"
            )

    def _build_training_config(self) -> Optional[TrainingConfig]:
        bm_data = self.base_model_combo.currentData()
        if not isinstance(bm_data, dict):
            return None

        ds_info: Optional[DatasetVersionInfo] = self.dataset_combo.currentData()
        if ds_info is None:
            # Exportera automatiskt version v1 om användaren inte manuellt har klickat på Exportera
            ds_info = self.dataset_manager.export_new_version(
                export_format=self.quick_export_fmt.currentText()
            )
            self.refresh_datasets_and_models()

        return TrainingConfig(
            base_model_name=bm_data["name"],
            model_family=bm_data["family"],
            base_weights=bm_data["weights"],
            dataset_version=ds_info.version,
            dataset_path=ds_info.path,
            epochs=int(self.epochs_spin.value()),
            batch_size=int(self.batch_spin.value()),
            image_size=int(self.imgsz_combo.currentText()),
            learning_rate=float(self.lr_spin.value()),
            pause_detection_during_training=bool(self.pause_detection_cb.isChecked()),
            schedule_mode=str(self.schedule_combo.currentData() or "immediate"),
        )

    def _on_start_clicked(self) -> None:
        cfg = self._build_training_config()
        if cfg is None:
            return

        if cfg.schedule_mode == "immediate":
            self.log_output.clear()
            self.progress_bar.setValue(0)
            self.start_training_requested.emit(cfg)
        else:
            self.schedule_training_requested.emit(cfg)
            QMessageBox.information(
                self,
                "Träning Schemalagd",
                f"Träningsjobbet för {cfg.base_model_name} på Dataset v{cfg.dataset_version} har lagts i kö ({cfg.schedule_mode}).",
            )

    def set_training_running_state(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def on_training_progress(self, epoch: int, total_epochs: int, metrics: Dict[str, float], log_line: str) -> None:
        pct = int((epoch / float(max(1, total_epochs))) * 100)
        self.progress_bar.setValue(pct)
        self.log_output.appendPlainText(log_line)

        if metrics:
            parts = [f"{k}: {v:.4f}" for k, v in metrics.items()]
            self.metrics_label.setText(f"Epok {epoch}/{total_epochs}  —  " + "  |  ".join(parts))

    def on_training_completed(self, info: TrainedModelInfo) -> None:
        self.set_training_running_state(False)
        self.progress_bar.setValue(100)
        self.log_output.appendPlainText(
            f"\n✔ Träning klar! Modellvikter sparade med versionssiffra v{info.version}: {info.weights_path}"
        )
        self.refresh_datasets_and_models()
        QMessageBox.information(
            self,
            f"Träning slutförd – Modell v{info.version}",
            f"Träningen är klar!\n\n"
            f"• Modellversion: v{info.version} (matchar Dataset v{info.dataset_version})\n"
            f"• Modellfamilj: {info.model_family}\n"
            f"• Sparade vikter: {info.weights_path}\n\n"
            f"Modellen finns nu tillgänglig i Detektionsläget.",
        )

    def on_training_failed(self, error_msg: str) -> None:
        self.set_training_running_state(False)
        self.log_output.appendPlainText(f"\n✖ Träning avbruten/misslyckades: {error_msg}")
