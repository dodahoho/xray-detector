"""TrainingView – UI för träningsläget.

Välj basmodell + dataset + parametrar, starta/avbryt träning, se live-logg.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QSpinBox, QPlainTextEdit, QPushButton, QLabel, QProgressBar,
    QGroupBox,
)


class TrainingView(QWidget):
    """Träningsläget."""

    start_requested = Signal(str, str, int, int, int, int)
    # (model_path, dataset_version, epochs, imgsz, batch, device)
    training_finished = Signal(str)  # path till nya vikter
    training_failed = Signal(str)

    def __init__(
        self,
        base_models: list[str],
        datasets: list[dict],
        defaults: dict,
        parent=None,
    ):
        """
        base_models: list av paths (str) till .pt-basmodeller
        datasets: list av dict {version, num_images, num_objects, created}
        defaults: {epochs, imgsz, batch, device}
        """
        super().__init__(parent)
        self.base_models = base_models
        self.datasets = datasets
        self.defaults = defaults
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        # Konfig-grupp
        cfg = QGroupBox("Konfiguration")
        form = QFormLayout(cfg)

        self.model_combo = QComboBox()
        self.model_combo.addItems(self.base_models)
        form.addRow("Basmodell:", self.model_combo)

        self.dataset_combo = QComboBox()
        for d in self.datasets:
            label = (
                f"{d['version']}  ({d.get('num_images', 0)} bilder, "
                f"{d.get('num_objects', 0)} objekt)"
            )
            self.dataset_combo.addItem(label, d["version"])
        if not self.datasets:
            self.dataset_combo.addItem("(inga dataset – annotera först)")
        form.addRow("Dataset:", self.dataset_combo)

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 10000)
        self.epochs_spin.setValue(self.defaults.get("epochs", 100))
        form.addRow("Epochs:", self.epochs_spin)

        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(320, 2048)
        self.imgsz_spin.setSingleStep(32)
        self.imgsz_spin.setValue(self.defaults.get("imgsz", 640))
        form.addRow("Bildstorlek:", self.imgsz_spin)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 256)
        self.batch_spin.setValue(self.defaults.get("batch", 16))
        form.addRow("Batch:", self.batch_spin)

        self.device_spin = QSpinBox()
        self.device_spin.setRange(-1, 8)
        self.device_spin.setValue(self.defaults.get("device", 0))
        self.device_spin.setSpecialValueText("CPU")
        form.addRow("Enhet:", self.device_spin)

        root.addWidget(cfg)

        # Status + progress
        status_row = QHBoxLayout()
        self.status_label = QLabel("Klar att starta")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        status_row.addWidget(self.status_label, stretch=1)
        status_row.addWidget(self.progress, stretch=1)
        root.addLayout(status_row)

        # Logg
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        root.addWidget(self.log_view, stretch=1)

        # Knappar
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Starta träning")
        self.start_btn.clicked.connect(self.start_training)
        self.stop_btn = QPushButton("Avbryt")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_training)
        btn_row.addStretch(1)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.start_btn)
        root.addLayout(btn_row)

    # ---- Logg ----
    def append_log(self, msg: str) -> None:
        self.log_view.appendPlainText(msg)

    def _append_log(self, msg: str) -> None:
        self.append_log(msg)

    # ---- Start/stop ----
    def start_training(self) -> None:
        ds_version = self.dataset_combo.currentData()
        if not ds_version:
            self.status_label.setText("Välj ett dataset")
            return
        self.start_requested.emit(
            self.model_combo.currentText(),
            ds_version,
            self.epochs_spin.value(),
            self.imgsz_spin.value(),
            self.batch_spin.value(),
            self.device_spin.value(),
        )

    def set_running(self, running: bool) -> None:
        """Appen uppdaterar UI-läge när träning startar/slutar."""
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        if running:
            self.status_label.setText("Träning pågår...")
            self.progress.setValue(0)
            self._append_log("=== Träning startar ===")

    def set_progress(self, frac: float) -> None:
        self.progress.setValue(int(frac * 100))

    def set_finished(self, path: str) -> None:
        self.status_label.setText(f"Klart! Vikter: {path}")
        self._append_log(f"=== Träning slutförd: {path} ===")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def set_failed(self, msg: str) -> None:
        self.status_label.setText("Träning misslyckades")
        self._append_log(f"=== FEL: {msg} ===")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def stop_training(self) -> None:
        self._append_log("Avbrott begärt...")
