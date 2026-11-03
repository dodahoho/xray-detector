"""Dataset export dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xray_detector.application.dataset_service import DatasetService
from xray_detector.config import AppConfig


class ExportDialog(QDialog):
    def __init__(
        self,
        config: AppConfig,
        dataset_service: DatasetService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.dataset_service = dataset_service
        self.setWindowTitle("Exportera dataset")
        self.resize(620, 320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.dataset_combo = QComboBox()
        form.addRow("Dataset:", self.dataset_combo)
        self.version_combo = QComboBox()
        form.addRow("Version:", self.version_combo)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["COCO + YOLO", "COCO", "YOLO"])
        form.addRow("Format:", self.format_combo)

        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit(str(config.exports_dir))
        dir_row.addWidget(self.dir_edit)
        browse = QPushButton("...")
        browse.clicked.connect(self._browse)
        dir_row.addWidget(browse)
        form.addRow("Målmapp:", dir_row)

        self.info_label = QLabel(
            "Exporten skapar en manifestfil med version, datum och antal bildobjekt."
        )
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #858595;")
        form.addRow("", self.info_label)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        self.export_button = buttons.addButton("Exportera", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.export_button.clicked.connect(self.export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.dataset_combo.currentTextChanged.connect(self._refresh_versions)
        self._refresh_datasets()

    def _refresh_datasets(self) -> None:
        datasets = self.dataset_service.list_datasets()
        self.dataset_combo.clear()
        self.dataset_combo.addItems(datasets)
        if self.config.app.dataset in datasets:
            self.dataset_combo.setCurrentText(self.config.app.dataset)
        self._refresh_versions()

    def _refresh_versions(self) -> None:
        self.version_combo.clear()
        name = self.dataset_combo.currentText()
        if not name:
            return
        for summary in self.dataset_service.list_versions(name):
            self.version_combo.addItem(
                f"{summary.version} ({summary.annotation_count} objekt)", summary.version
            )

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Välj exportmapp", self.dir_edit.text())
        if path:
            self.dir_edit.setText(path)

    def export(self) -> None:
        name = self.dataset_combo.currentText()
        version = self.version_combo.currentData()
        target = self.dir_edit.text().strip()
        if not name or not version:
            QMessageBox.warning(self, "Export", "Välj dataset och version.")
            return
        if not target:
            QMessageBox.warning(self, "Export", "Välj en målmapp.")
            return
        destination = Path(target)
        fmt = self.format_combo.currentText()
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            if fmt == "COCO + YOLO":
                manifests = self.dataset_service.export_both(version, destination, name)
                summary = "\n".join(
                    f"{key.upper()}: {manifest['annotation_count']} objekt, "
                    f"{manifest['image_count']} bilder"
                    for key, manifest in manifests.items()
                )
            else:
                selected = "coco" if fmt == "COCO" else "yolo"
                manifest = self.dataset_service.export(version, selected, destination, name)
                summary = (
                    f"{fmt}: {manifest['annotation_count']} objekt, "
                    f"{manifest['image_count']} bilder\nMapp: {destination}"
                )
        except Exception as exc:
            QMessageBox.critical(self, "Export misslyckades", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Export klar", summary)
        self.accept()
