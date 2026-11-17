"""Modellistan i de globala inställningarna (TASK-81, TASK-115).

Sektionen listar modellerna som väljarna i detektionsvyn bygger sina listor ur,
och låter användaren lägga till en viktfil från disk eller en adress, byta
visningsnamn och ta bort en modell. Ändringarna skrivs direkt till
models/models.json, så vyerna kan bygga om sina väljare på en gång.

Egentränade modeller listas också. De hittas genom sina träningsmanifest under
models/trained/ och namnet sätts vid träningen, så de kan inte bytas namn på
här. De kan tas bort, och då raderas träningsfilerna på samma sätt som när
körningen tas bort i träningsvyn (TASK-119).
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
    QMessageBox,
    QVBoxLayout,
)

from xray_detector.application.background_task import BackgroundTask
from xray_detector.application.model_registry import (
    ModelCatalog,
    ModelSpec,
    available_models,
    is_trained,
    trained_run_id,
)
from xray_detector.application.training_history import delete_run
from xray_detector.ui.colors import MUTED_TEXT
from xray_detector.ui.shortcuts import mnemonic
from xray_detector.ui.style import LIST_MAX_WIDTH, button
from xray_detector.ui.training_history import is_active_run

WEIGHT_FILTER = "Modellvikter (*.pt *.pth)"
FAMILY_LABELS = {"yolo": "YOLO", "rfdetr": "RF-DETR"}
LIST_MAX_HEIGHT = 220
MUTED_COLOR = MUTED_TEXT
TRAINED_HINT = (
    "Egentränad modell: namnet sätts vid träningen och kan därför inte bytas "
    "här. Ta bort raderar även träningsfilerna."
)
TRAINED_REMOVE_QUESTION = (
    "{label} är en egentränad modell.\n\n"
    "Borttagningen raderar även träningsfilerna: vikter, manifest, metrics och "
    "utvärdering. Det går inte att ångra."
)
# dialogen har ingen egen hjälptext, så instruktionen står i etiketten
URL_HINT = (
    "Adress till viktfilen. Den måste sluta på .pt (YOLO)\n"
    "eller .pth (RF-DETR) och vara en nedladdningslänk,\n"
    "inte en webbsida.\n"
    "\n"
    "Exempel från Huggingface:\n"
    "https://huggingface.co/Ultralytics/YOLO26/resolve/main/yolo26l.pt"
)


class ModelSection(QGroupBox):
    """Modellistan: lägg till, byt namn och ta bort modeller (TASK-81).

    En nedladdning kan ta minuter, så tilläggen körs i trådpoolen och knapparna
    är avstängda under tiden. Borttagningen av en basmodell rör bara listan:
    viktfilen ligger kvar i models/, så en modell som togs bort av misstag går
    att lägga till igen utan att laddas ner på nytt.

    Listan är densamma som detektionsvyns väljare bygger på (TASK-115), så
    egentränade modeller syns här också. De ägs av sina träningsmanifest, så
    namnet sätts vid träningen; att ta bort en sådan modell raderar
    träningsfilerna, precis som i träningsvyn (TASK-119).
    """

    models_changed = Signal()

    def __init__(
        self,
        models_dir: Path,
        trained_dir: Path | None = None,
        parent=None,
        active_run_dir=None,
    ) -> None:
        super().__init__("Modeller", parent)
        self.setMaximumWidth(LIST_MAX_WIDTH)
        self.catalog = ModelCatalog(models_dir)
        #: Katalogen för körningen som pågår just nu, så den inte kan tas bort
        #: medan träningen skriver i den (TASK-129).
        self.active_run_dir = active_run_dir or (lambda: None)
        # samma standard som AppConfig.trained_dir
        self.trained_dir = (
            Path(trained_dir)
            if trained_dir is not None
            else self.catalog.models_dir / "trained"
        )
        self._specs: dict[str, ModelSpec] = {}
        self._task: BackgroundTask | None = None
        self._busy = False
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setMaximumHeight(LIST_MAX_HEIGHT)
        self.list.currentRowChanged.connect(self._update_buttons)
        layout.addWidget(self.list)
        self.trained_hint = QLabel(TRAINED_HINT)
        self.trained_hint.setWordWrap(True)
        self.trained_hint.setStyleSheet(f"color: {MUTED_COLOR};")
        self.trained_hint.setVisible(False)
        layout.addWidget(self.trained_hint)
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
        self._specs = {}
        for spec in available_models(self.catalog.models_dir, self.trained_dir):
            item = QListWidgetItem(spec.label)
            item.setData(Qt.ItemDataRole.UserRole, spec.key)
            item.setToolTip(self._tooltip(spec))
            self.list.addItem(item)
            self._specs[spec.key] = spec
        self.list.blockSignals(False)
        self._select(current)
        self._update_buttons()

    @staticmethod
    def _tooltip(spec: ModelSpec) -> str:
        """Familj och viktfil; en egentränad modell märks ut som sådan."""
        text = f"{FAMILY_LABELS.get(spec.family, spec.family)}: {spec.weights}"
        return f"{text}\nEgentränad modell" if is_trained(spec) else text

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
        spec = self._current_spec()
        # en egentränad modell får sitt namn vid träningen, men kan tas bort
        # med sina träningsfiler (TASK-119)
        trained = spec is not None and is_trained(spec)
        self.rename_button.setEnabled(spec is not None and not trained and not self._busy)
        self.remove_button.setEnabled(spec is not None and not self._busy)
        self.trained_hint.setVisible(trained)

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
            self, "Lägg till modell från internet", URL_HINT
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
        if spec is None or is_trained(spec):
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
        """Tar bort modellen; en egentränad modell tar sina träningsfiler med sig (TASK-119)."""
        spec = self._current_spec()
        if spec is None:
            return
        run_id = trained_run_id(spec)
        if run_id is not None:
            if is_active_run(self.trained_dir / run_id, self.active_run_dir):
                self.status.setText(
                    f"{spec.label} tränas just nu och kan inte tas bort förrän träningen är klar"
                )
                return
            if not self._confirm_trained_removal(spec):
                return
            try:
                delete_run(self.trained_dir, run_id)
            except OSError as exc:
                self.status.setText(f"Kunde inte ta bort träningen: {exc}")
                return
            self.refresh()
            self.status.setText(f"Borttagen med träningsfilerna: {spec.label}")
        else:
            self.catalog.remove(spec.key)
            self.refresh()
            self.status.setText(f"Borttagen ur listan: {spec.label}")
        self.models_changed.emit()

    def _confirm_trained_removal(self, spec: ModelSpec) -> bool:
        """Varnar att en egentränad modell tar sina träningsfiler med sig (TASK-119)."""
        answer = QMessageBox.warning(
            self,
            "Ta bort egentränad modell",
            TRAINED_REMOVE_QUESTION.format(label=spec.label),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Ok

    def _current_spec(self) -> ModelSpec | None:
        key = self.current_key()
        return None if key is None else self._specs.get(key)
