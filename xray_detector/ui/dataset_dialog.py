"""DatasetDialog – visa datasetversioner, skapa ny, exportera till YOLO."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox,
)

from xray_detector.dataset.dataset_manager import DatasetManager
from xray_detector.dataset.yolo_export import export_yolo


class DatasetDialog(QDialog):
    """Dialog för att hantera datasetversioner."""

    export_requested = Signal(str)  # version som exporterades

    def __init__(self, manager: DatasetManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Dataset")
        self.setMinimumSize(640, 420)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        root.addWidget(QLabel("Datasetversioner (COCO-format):"))

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Version", "Bilder", "Objekt", "Skapad"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        root.addWidget(self.table, stretch=1)

        # Knappar
        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("Ny version")
        self.new_btn.clicked.connect(self._new_version)
        self.export_btn = QPushButton("Exportera till YOLO")
        self.export_btn.clicked.connect(self._export)
        self.delete_btn = QPushButton("Radera")
        self.delete_btn.clicked.connect(self._delete)
        self.close_btn = QPushButton("Stäng")
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.new_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)

    def refresh(self) -> None:
        versions = self.manager.list_versions()
        self.table.setRowCount(len(versions))
        for row, v in enumerate(versions):
            meta = self.manager.metadata(v)
            self.table.setItem(row, 0, QTableWidgetItem(v))
            self.table.setItem(row, 1, QTableWidgetItem(str(meta.get("num_images", 0))))
            self.table.setItem(row, 2, QTableWidgetItem(str(meta.get("num_objects", 0))))
            self.table.setItem(row, 3, QTableWidgetItem(str(meta.get("created", ""))))

    def _selected_version(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 0).text()

    def _new_version(self) -> None:
        v = self.manager.next_version()
        self.manager.create_version(categories=None)
        self.refresh()
        QMessageBox.information(self, "Ny version", f"Skapade {v}")

    def _export(self) -> None:
        v = self._selected_version()
        if not v:
            QMessageBox.warning(self, "Export", "Välj en version först")
            return
        ds = self.manager.open(v)
        if not ds.images:
            QMessageBox.warning(self, "Export", "Versionen har inga bilder")
            return
        out = export_yolo(ds)
        self.export_requested.emit(v)
        QMessageBox.information(self, "Export klar", f"YOLO-export: {out}")

    def _delete(self) -> None:
        v = self._selected_version()
        if not v:
            return
        reply = QMessageBox.question(
            self, "Radera", f"Radera datasetversion {v}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.manager.delete_version(v)
            self.refresh()
