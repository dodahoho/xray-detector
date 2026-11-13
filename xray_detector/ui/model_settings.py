"""Modellistan i de globala inställningarna (TASK-81).

Sektionen listar modellerna som väljarna i detektions- och träningsvyn bygger
sina listor ur, och låter användaren lägga till en viktfil från disk eller en
adress, byta visningsnamn och ta bort en modell. Ändringarna skrivs direkt till
models/models.json, så vyerna kan bygga om sina väljare på en gång.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from xray_detector.application.background_task import BackgroundTask
from xray_detector.application.model_registry import ModelCatalog
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import LIST_MAX_WIDTH, button

WEIGHT_FILTER = "Modellvikter (*.pt *.pth)"
FAMILY_LABELS = {"yolo": "YOLO", "rfdetr": "RF-DETR"}
LIST_MAX_HEIGHT = 220
MUTED_COLOR = "#888"


class ModelSection(QGroupBox):
    """Modellistan: lägg till, byt namn och ta bort modeller (TASK-81).

    En nedladdning kan ta minuter, så tilläggen körs i trådpoolen och knapparna
    är avstängda under tiden. Borttagningen rör bara listan: viktfilen ligger
    kvar i models/, så en modell som togs bort av misstag går att lägga till
    igen utan att laddas ner på nytt.
    """

    models_changed = Signal()

    def __init__(self, models_dir: Path, parent=None) -> None:
        super().__init__("Modeller", parent)
        self.setMaximumWidth(LIST_MAX_WIDTH)
        self.catalog = ModelCatalog(models_dir)
        self._task: BackgroundTask | None = None
        self._busy = False
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setMaximumHeight(LIST_MAX_HEIGHT)
        self.list.currentRowChanged.connect(self._update_buttons)
        layout.addWidget(self.list)
        row = QHBoxLayout()
        self.add_file_button = button(mnemonic("Lägg till från fil...", "f"))
        self.add_file_button.clicked.connect(self._on_add_file)
        self.add_url_button = button(mnemonic("Hämta från internet...", "h"))
        self.add_url_button.clicked.connect(self._on_add_url)
        self.rename_button = button(mnemonic("Byt namn...", "n"))
        self.rename_button.clicked.connect(self._on_rename)
        self.remove_button = button(mnemonic("Ta bort", "b"))
        self.remove_button.clicked.connect(self._on_remove)
        for widget in (
            self.add_file_button,
            self.add_url_button,
            self.rename_button,
            self.remove_button,
        ):
            row.addWidget(widget)
        row.addStretch(1)
        layout.addLayout(row)
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {MUTED_COLOR};")
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self) -> None:
        """Bygger om listan ur katalogen och behåller markeringen om den finns kvar."""
        current = self.current_key()
        self.list.blockSignals(True)
        self.list.clear()
        for spec in self.catalog.specs():
            item = QListWidgetItem(spec.label)
            item.setData(Qt.ItemDataRole.UserRole, spec.key)
            item.setToolTip(
                f"{FAMILY_LABELS.get(spec.family, spec.family)}: {spec.weights}"
            )
            self.list.addItem(item)
        self.list.blockSignals(False)
        self._select(current)
        self._update_buttons()

    def current_key(self) -> str | None:
        item = self.list.currentItem()
        return None if item is None else item.data(Qt.ItemDataRole.UserRole)

    def wait_for_download(self, timeout_ms: int = 10000) -> None:
        """Väntar in en pågående nedladdning (tester och stängning)."""
        if self._task is not None:
            self._task.wait(timeout_ms)

    def _select(self, key: str | None) -> None:
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.ItemDataRole.UserRole) == key:
                self.list.setCurrentRow(row)
                return
        if self.list.count():
            self.list.setCurrentRow(0)

    def _update_buttons(self, *_args) -> None:
        has_selection = self.current_key() is not None
        for widget in (self.rename_button, self.remove_button):
            widget.setEnabled(has_selection and not self._busy)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for widget in (self.add_file_button, self.add_url_button):
            widget.setEnabled(not busy)
        self._update_buttons()

    def _run(self, work, message: str) -> None:
        """Kör ett tillägg i trådpoolen, så en nedladdning inte låser GUI:t."""
        self._set_busy(True)
        self.status.setText(message)
        self._task = BackgroundTask(work)
        self._task.succeeded.connect(self._on_added)
        self._task.failed.connect(self._on_failed)
        self._task.finished.connect(lambda: self._set_busy(False))
        self._task.start()

    def _on_add_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Lägg till modell från fil", "", WEIGHT_FILTER
        )
        if not path:
            return
        self._run(lambda: self.catalog.add_local(Path(path)), "Lägger till modellen...")

    def _on_add_url(self) -> None:
        url, ok = QInputDialog.getText(
            self, "Lägg till modell från internet", "Adress (http/https):"
        )
        if not ok or not url.strip():
            return
        self._run(
            lambda: self.catalog.add_from_url(url.strip()), "Laddar ner modellen..."
        )

    def _on_added(self, spec) -> None:
        self.refresh()
        self._select(spec.key)
        self.status.setText(f"Tillagd: {spec.label}")
        self.models_changed.emit()

    def _on_failed(self, message: str) -> None:
        self.status.setText(f"Kunde inte lägga till modellen: {message}")

    def _on_rename(self) -> None:
        spec = self._current_spec()
        if spec is None:
            return
        label, ok = QInputDialog.getText(
            self, "Byt visningsnamn", "Visningsnamn:", text=spec.label
        )
        if not ok or not label.strip() or label.strip() == spec.label:
            return
        self.catalog.rename(spec.key, label)
        self.refresh()
        self._select(spec.key)
        self.status.setText(f"Visningsnamn: {label.strip()}")
        self.models_changed.emit()

    def _on_remove(self) -> None:
        spec = self._current_spec()
        if spec is None:
            return
        self.catalog.remove(spec.key)
        self.refresh()
        self.status.setText(f"Borttagen ur listan: {spec.label}")
        self.models_changed.emit()

    def _current_spec(self):
        key = self.current_key()
        if key is None:
            return None
        return next((spec for spec in self.catalog.specs() if spec.key == key), None)
