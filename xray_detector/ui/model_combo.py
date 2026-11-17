"""Modellväljaren som delas av detektions- och träningsvyn (TASK-140).

Båda vyerna byggde samma QComboBox ur modellistan och inaktiverade RF-DETR på
samma sätt när paketet saknades. Skillnaden var bara vilken text som lades
till, så regeln bor här i stället för i två kopior.
"""

import importlib.util

from PySide6.QtWidgets import QComboBox

from xray_detector.application.model_registry import ModelSpec

#: Familjer vars paket måste vara installerat för att modellen ska gå att välja.
OPTIONAL_FAMILIES = {"rfdetr": "rfdetr"}


def missing_packages() -> dict[str, bool]:
    """Vilka valfria modellfamiljer som saknar sitt paket i den här miljön."""
    return {
        family: importlib.util.find_spec(package) is None
        for family, package in OPTIONAL_FAMILIES.items()
    }


class ModelComboBox(QComboBox):
    """Modellväljare som fyller sig ur modellistan och stänger av saknade paket."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.specs: dict[str, ModelSpec] = {}

    def fill(self, specs: list[ModelSpec], current: str | None = None) -> None:
        """Bygger om listan och behåller valet om modellen finns kvar."""
        self.blockSignals(True)
        self.clear()
        self.specs = {}
        for spec in specs:
            self.addItem(spec.label, spec.key)
            self.specs[spec.key] = spec
        self._disable_missing_packages()
        index = self.findData(current) if current else -1
        if index >= 0:
            self.setCurrentIndex(index)
        self.blockSignals(False)

    def _disable_missing_packages(self) -> None:
        """Stänger av modeller vars paket saknas och märker posten i texten."""
        missing = missing_packages()
        model = self.model()
        for row in range(model.rowCount()):
            spec = self.specs.get(self.itemData(row))
            if spec is None or not missing.get(spec.family, False):
                continue
            item = model.item(row)
            item.setEnabled(False)
            self.setItemText(row, f"{item.text()} ({spec.family} ej installerat)")

    def spec(self) -> ModelSpec | None:
        """Modellen som är vald, eller None."""
        return self.specs.get(self.currentData())

    def enabled(self, index: int) -> bool:
        """Om posten på index går att välja."""
        item = self.model().item(index)
        return item is not None and item.isEnabled()
