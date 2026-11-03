from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
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

from xray_detector.dataset.versioning import DatasetMetadata


class ExportDialog(QDialog):
    def __init__(
        self,
        metadata: DatasetMetadata,
        default_directory: Path,
        parent=None,
    ) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Exportera dataset")
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        info = QLabel(
            f"Dataset: {metadata.dataset_id}\n"
            f"Version: {metadata.version} (revision {metadata.revision})\n"
            f"Bilder: {metadata.image_count} · Annotationer: {metadata.annotation_count}\n"
            f"Klasser: {len(metadata.categories)}"
        )
        info.setStyleSheet("padding: 8px; background: #eeeeee; border-radius: 4px;")
        root.addWidget(info)

        form = QFormLayout()
        self.coco = QCheckBox("COCO (annotations.json)")
        self.coco.setChecked(True)
        self.yolo = QCheckBox("YOLO (labels + data.yaml)")
        self.yolo.setChecked(True)
        formats = QWidget()
        formats_layout = QVBoxLayout(formats)
        formats_layout.setContentsMargins(0, 0, 0, 0)
        formats_layout.addWidget(self.coco)
        formats_layout.addWidget(self.yolo)
        form.addRow("Format:", formats)

        directory_row = QHBoxLayout()
        self.directory = QLineEdit(str(default_directory))
        directory_row.addWidget(self.directory, 1)
        browse = QPushButton("Bläddra...")
        browse.clicked.connect(self._browse)
        directory_row.addWidget(browse)
        directory_widget = QWidget()
        directory_widget.setLayout(directory_row)
        form.addRow("Exportkatalog:", directory_widget)

        self.archive = QCheckBox("Skapa zip-arkiv")
        form.addRow("", self.archive)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Välj exportkatalog", self.directory.text()
        )
        if path:
            self.directory.setText(path)

    def _accept(self) -> None:
        if not self.coco.isChecked() and not self.yolo.isChecked():
            QMessageBox.warning(self, "Export", "Välj minst ett format.")
            return
        if not self.directory.text().strip():
            QMessageBox.warning(self, "Export", "Välj en exportkatalog.")
            return
        self.accept()

    def values(self) -> tuple[Path, tuple[str, ...], bool]:
        formats: list[str] = []
        if self.coco.isChecked():
            formats.append("coco")
        if self.yolo.isChecked():
            formats.append("yolo")
        return Path(self.directory.text().strip()).expanduser(), tuple(formats), self.archive.isChecked()
