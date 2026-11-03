from __future__ import annotations

from typing import List, Optional
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.models_schema import CapturedFramePair
from src.dataset.dataset_manager import DatasetManager
from src.ui.annotation_canvas import AnnotationCanvas, EditableBoxItem


class AnnotationView(QWidget):
    """Annoteringsläge: Två frysta bilder med redigerbara rektanglar, klasshantering och datasetexport."""

    saved_and_return = Signal()  # Emitted när användaren sparar till dataset och återgår till detektionsläget
    dataset_exported = Signal(object)  # DatasetVersionInfo

    def __init__(self, dataset_manager: DatasetManager, parent=None) -> None:
        super().__init__(parent)
        self.dataset_manager = dataset_manager
        self._frame_1: Optional[np.ndarray] = None
        self._frame_2: Optional[np.ndarray] = None
        self._active_selected_item: Optional[EditableBoxItem] = None

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(12)

        # Vänster/Mitten: De två frysta bilderna i split-screen
        canvases_container = QWidget()
        canvases_layout = QVBoxLayout(canvases_container)
        canvases_layout.setContentsMargins(0, 0, 0, 0)
        canvases_layout.setSpacing(8)

        instr_banner = QLabel(
            "💡 Tips: Befintliga detektioner är inritade. Dra i ett hörn eller en kant på en rektangel för att ändra storlek. "
            "Klicka och dra på fri yta i bilden för att rita en ny rektangel."
        )
        instr_banner.setWordWrap(True)
        instr_banner.setStyleSheet(
            "background-color: #182232; color: #93c5fd; padding: 8px 12px; border-radius: 6px; border: 1px solid #2563eb; font-size: 13px;"
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Ström 1 Canvas
        s1_box = QWidget()
        s1_layout = QVBoxLayout(s1_box)
        s1_layout.setContentsMargins(0, 0, 0, 0)
        self.s1_header = QLabel("Fryst bild – Ström 1 (Vy A)")
        self.s1_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #e2e8f0;")
        self.canvas_1 = AnnotationCanvas(1, "Ström 1")
        s1_layout.addWidget(self.s1_header)
        s1_layout.addWidget(self.canvas_1, stretch=1)

        # Ström 2 Canvas
        s2_box = QWidget()
        s2_layout = QVBoxLayout(s2_box)
        s2_layout.setContentsMargins(0, 0, 0, 0)
        self.s2_header = QLabel("Fryst bild – Ström 2 (Vy B)")
        self.s2_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #e2e8f0;")
        self.canvas_2 = AnnotationCanvas(2, "Ström 2")
        s2_layout.addWidget(self.s2_header)
        s2_layout.addWidget(self.canvas_2, stretch=1)

        splitter.addWidget(s1_box)
        splitter.addWidget(s2_box)
        splitter.setSizes([600, 600])

        canvases_layout.addWidget(instr_banner)
        canvases_layout.addWidget(splitter, stretch=1)

        # Höger sidopanel: Klassval, ny klass, spara och exportera dataset
        side_panel = QFrame()
        side_panel.setFixedWidth(340)
        side_panel.setStyleSheet(
            "QFrame { background-color: #18202c; border: 1px solid #2b374b; border-radius: 8px; }"
        )
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)

        cls_title = QLabel("Objektklasser")
        cls_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc; border: none;")

        cls_sub = QLabel("Välj klass för ny rektangel eller ändra klass på markerad rektangel:")
        cls_sub.setWordWrap(True)
        cls_sub.setStyleSheet("font-size: 12px; color: #94a3b8; border: none;")

        self.class_list = QListWidget()
        self.class_list.setStyleSheet(
            """
            QListWidget {
                background-color: #0f141b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 7px 10px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
            }
            """
        )
        self.class_list.currentTextChanged.connect(self._on_class_selected_from_list)

        # Lägg till helt ny klass
        new_cls_row = QHBoxLayout()
        self.new_class_input = QLineEdit()
        self.new_class_input.setPlaceholderText("Skriv in ny klass...")
        self.new_class_input.setStyleSheet(
            "background-color: #0f141b; color: #f8fafc; padding: 6px 8px; border: 1px solid #3b4b64; border-radius: 5px;"
        )
        self.new_class_input.returnPressed.connect(self._on_add_new_class)

        self.add_class_btn = QPushButton("+ Ny klass")
        self.add_class_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_class_btn.setStyleSheet(
            "background-color: #334155; color: #f8fafc; font-weight: bold; padding: 6px 12px; border-radius: 5px;"
        )
        self.add_class_btn.clicked.connect(self._on_add_new_class)
        new_cls_row.addWidget(self.new_class_input, stretch=1)
        new_cls_row.addWidget(self.add_class_btn)

        # Info & borttagning för markerad rektangel
        self.selected_box_label = QLabel("Markerad rektangel: Ingen")
        self.selected_box_label.setWordWrap(True)
        self.selected_box_label.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold; border: none;")

        self.delete_box_btn = QPushButton("🗑 Ta bort markerad rektangel (Del)")
        self.delete_box_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_box_btn.setStyleSheet(
            "background-color: #7f1d1d; color: #fecaca; padding: 7px; border-radius: 5px; font-weight: bold;"
        )
        self.delete_box_btn.clicked.connect(self._delete_selected_box)

        # Dataset-status & Export (COCO / YOLO)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #334155;")

        ds_title = QLabel("Dataset & Export (COCO / YOLO)")
        ds_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc; border: none;")

        self.working_stats_label = QLabel("Arbetsdataset: 0 bilder, 0 objekt")
        self.working_stats_label.setStyleSheet("color: #cbd5e1; font-size: 12px; border: none;")

        export_row = QHBoxLayout()
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["COCO+YOLO", "COCO", "YOLO"])
        self.export_format_combo.setStyleSheet(
            "background-color: #0f141b; color: #f8fafc; padding: 5px 8px; border: 1px solid #3b4b64; border-radius: 5px;"
        )
        self.export_btn = QPushButton("📦 Exportera version")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setStyleSheet(
            "background-color: #0d9488; color: #ffffff; font-weight: bold; padding: 6px 10px; border-radius: 5px;"
        )
        self.export_btn.clicked.connect(self._on_export_dataset_clicked)
        export_row.addWidget(self.export_format_combo)
        export_row.addWidget(self.export_btn, stretch=1)

        self.latest_export_info = QLabel("Senaste export: Ingen")
        self.latest_export_info.setWordWrap(True)
        self.latest_export_info.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")

        # Spara och återgå till detektionsläge
        self.save_btn = QPushButton("💾  SPARA TILL DATASET && ÅTERGÅ")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setMinimumHeight(48)
        self.save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #16a34a;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border-radius: 7px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
            """
        )
        self.save_btn.clicked.connect(self.save_and_return_to_detection)

        self.cancel_btn = QPushButton("Avbryt (Återgå utan att spara)")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet(
            "background-color: #334155; color: #e2e8f0; padding: 7px; border-radius: 5px;"
        )
        self.cancel_btn.clicked.connect(self.saved_and_return.emit)

        side_layout.addWidget(cls_title)
        side_layout.addWidget(cls_sub)
        side_layout.addWidget(self.class_list, stretch=1)
        side_layout.addLayout(new_cls_row)
        side_layout.addWidget(self.selected_box_label)
        side_layout.addWidget(self.delete_box_btn)
        side_layout.addWidget(sep)
        side_layout.addWidget(ds_title)
        side_layout.addWidget(self.working_stats_label)
        side_layout.addLayout(export_row)
        side_layout.addWidget(self.latest_export_info)
        side_layout.addSpacing(4)
        side_layout.addWidget(self.save_btn)
        side_layout.addWidget(self.cancel_btn)

        main_layout.addWidget(canvases_container, stretch=1)
        main_layout.addWidget(side_panel)

        # Koppla signaler från båda ritvyerna
        self.canvas_1.box_selected.connect(lambda item: self._on_canvas_box_selected(1, item))
        self.canvas_2.box_selected.connect(lambda item: self._on_canvas_box_selected(2, item))
        self.canvas_1.boxes_changed.connect(self._update_headers)
        self.canvas_2.boxes_changed.connect(self._update_headers)

        self.refresh_classes_and_stats()

    def refresh_classes_and_stats(self) -> None:
        current_text = self.class_list.currentItem().text() if self.class_list.currentItem() else ""
        classes = self.dataset_manager.get_classes()

        self.class_list.blockSignals(True)
        self.class_list.clear()
        for cls_name in classes:
            self.class_list.addItem(QListWidgetItem(cls_name))

        if current_text and current_text in classes:
            idx = classes.index(current_text)
            self.class_list.setCurrentRow(idx)
        elif classes:
            self.class_list.setCurrentRow(0)
        self.class_list.blockSignals(False)

        active_cls = self.class_list.currentItem().text() if self.class_list.currentItem() else "Metallföremål"
        self.canvas_1.set_active_class_for_new_boxes(active_cls)
        self.canvas_2.set_active_class_for_new_boxes(active_cls)

        num_imgs, num_objs = self.dataset_manager.get_working_stats()
        self.working_stats_label.setText(f"Arbetsdataset (COCO): {num_imgs} bilder, {num_objs} bildobjekt")

        versions = self.dataset_manager.list_exported_versions()
        if versions:
            latest = versions[0]
            self.latest_export_info.setText(
                f"Senaste export: v{latest.version} ({latest.created_at}) – "
                f"{latest.num_images} bilder, {latest.num_objects} bildobjekt [{latest.export_format}]"
            )
        else:
            self.latest_export_info.setText("Senaste export: Ingen exporterad version ännu")

    def load_captured_pair(self, pair: CapturedFramePair) -> None:
        """Laddar in det fångade bildparet och ritar automatiskt in befintliga detektioner."""
        self._frame_1 = pair.stream_1_frame.copy()
        self._frame_2 = pair.stream_2_frame.copy()
        self._active_selected_item = None

        # Säkerställ att eventuella detekterade klasser finns i klasslistan
        for b in pair.stream_1_boxes + pair.stream_2_boxes:
            self.dataset_manager.ensure_class(b.class_name)

        self.refresh_classes_and_stats()
        self.canvas_1.load_frozen_frame(self._frame_1, pair.stream_1_boxes)
        self.canvas_2.load_frozen_frame(self._frame_2, pair.stream_2_boxes)
        self.selected_box_label.setText("Markerad rektangel: Ingen (klicka på en rektangel för att redigera)")
        self._update_headers()

    def _update_headers(self) -> None:
        b1 = len(self.canvas_1.get_boxes())
        b2 = len(self.canvas_2.get_boxes())
        self.s1_header.setText(f"Fryst bild – Ström 1 (Vy A)  |  {b1} annoterade objekt")
        self.s2_header.setText(f"Fryst bild – Ström 2 (Vy B)  |  {b2} annoterade objekt")

    def _on_canvas_box_selected(self, stream_id: int, item: Optional[EditableBoxItem]) -> None:
        if stream_id == 1 and item is not None:
            self.canvas_2.clear_selection()
        elif stream_id == 2 and item is not None:
            self.canvas_1.clear_selection()

        self._active_selected_item = item
        if item is not None:
            r = item.rect().normalized()
            self.selected_box_label.setText(
                f"Markerad (Ström {stream_id}): {item.class_name} "
                f"[{int(r.width())}x{int(r.height())} px]"
            )
            # Markera motsvarande klass i listan utan att trigga oändlig loop
            self.class_list.blockSignals(True)
            for i in range(self.class_list.count()):
                if self.class_list.item(i).text() == item.class_name:
                    self.class_list.setCurrentRow(i)
                    break
            self.class_list.blockSignals(False)
        else:
            self.selected_box_label.setText("Markerad rektangel: Ingen")

    def _on_class_selected_from_list(self, class_name: str) -> None:
        if not class_name:
            return
        self.canvas_1.set_active_class_for_new_boxes(class_name)
        self.canvas_2.set_active_class_for_new_boxes(class_name)

        # Om en rektangel är markerad ändras dess klass direkt!
        if self._active_selected_item is not None:
            self._active_selected_item.set_class_name(class_name)
            r = self._active_selected_item.rect().normalized()
            self.selected_box_label.setText(
                f"Markerad: {class_name} [{int(r.width())}x{int(r.height())} px]"
            )

    def _on_add_new_class(self) -> None:
        new_cls = self.new_class_input.text().strip()
        if not new_cls:
            return
        self.dataset_manager.ensure_class(new_cls)
        self.new_class_input.clear()
        self.refresh_classes_and_stats()

        # Välj den nya klassen och tilldela den till eventuell markerad rektangel
        for i in range(self.class_list.count()):
            if self.class_list.item(i).text().lower() == new_cls.lower():
                self.class_list.setCurrentRow(i)
                break

    def _delete_selected_box(self) -> None:
        if not self.canvas_1.delete_selected_box():
            self.canvas_2.delete_selected_box()
        self._active_selected_item = None
        self.selected_box_label.setText("Markerad rektangel: Ingen")

    def save_and_return_to_detection(self) -> None:
        """Sparar de två bilderna och samtliga inritade rektanglar till datasetet och återgår till detektionsläge."""
        if self._frame_1 is not None and self._frame_2 is not None:
            boxes_1 = self.canvas_1.get_boxes()
            boxes_2 = self.canvas_2.get_boxes()
            self.dataset_manager.add_annotated_frame_pair(
                frame_1_bgr=self._frame_1,
                boxes_1=boxes_1,
                frame_2_bgr=self._frame_2,
                boxes_2=boxes_2,
            )
            self.refresh_classes_and_stats()
        self.saved_and_return.emit()

    def _on_export_dataset_clicked(self) -> None:
        # Om det finns osparade bilder i vyn, fråga eller spara dem först om working-datasetet är tomt
        num_imgs, _ = self.dataset_manager.get_working_stats()
        if num_imgs == 0 and self._frame_1 is not None and self._frame_2 is not None:
            self.dataset_manager.add_annotated_frame_pair(
                frame_1_bgr=self._frame_1,
                boxes_1=self.canvas_1.get_boxes(),
                frame_2_bgr=self._frame_2,
                boxes_2=self.canvas_2.get_boxes(),
            )

        fmt = self.export_format_combo.currentText()
        info = self.dataset_manager.export_new_version(export_format=fmt)
        self.refresh_classes_and_stats()
        self.dataset_exported.emit(info)
        QMessageBox.information(
            self,
            f"Dataset Exporterat (v{info.version})",
            f"Datasetet har exporterats!\n\n"
            f"• Versionssiffra: v{info.version}\n"
            f"• Datum: {info.created_at}\n"
            f"• Antal bilder: {info.num_images}\n"
            f"• Antal bildobjekt: {info.num_objects}\n"
            f"• Format: {info.export_format}\n"
            f"• Sökväg: {info.path}",
        )
