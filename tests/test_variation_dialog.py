"""Dialogen för att utöka datasetet med bildvariationer (TASK-88)."""

import pytest
from PySide6.QtWidgets import QDialog, QPushButton

from xray_detector.domain.dataset import VariationSettings
from xray_detector.ui.variation_dialog import NO_VARIATIONS, VariationDialog


@pytest.fixture
def dialog(qapp) -> VariationDialog:
    return VariationDialog(3)


def test_dialog_starts_without_variations(dialog):
    """Inget händer förrän användaren anger ett antal."""
    assert dialog.settings() == VariationSettings(
        rotation_count=0,
        rotation_degrees=360.0,
        flip_horizontal=False,
        flip_vertical=False,
        scale_count=0,
        scale_percent=50.0,
        color_count=0,
        color_percent=20.0,
    )
    assert dialog.summary.text() == NO_VARIATIONS
    assert not dialog.extend_button.isEnabled()


def test_dialog_is_titled_after_the_button(dialog):
    assert dialog.windowTitle() == "Utöka med bildvariationer"


def test_counts_enable_the_extend_button(dialog):
    dialog.rotation_count.setValue(2)

    assert dialog.extend_button.isEnabled()
    assert dialog.summary.text() == (
        "2 variationer per bildpar ger 6 nya bildpar från 3 original."
    )


def test_flips_count_as_variations(dialog):
    """Vändningen har inget antal: de två riktningarna är var sin variation."""
    dialog.flip_horizontal.setChecked(True)
    dialog.flip_vertical.setChecked(True)

    assert dialog.settings().total == 2
    assert dialog.summary.text().startswith("2 variationer per bildpar")


def test_settings_reads_every_field(dialog):
    dialog.rotation_count.setValue(1)
    dialog.rotation_degrees.setValue(45)
    dialog.flip_horizontal.setChecked(True)
    dialog.scale_count.setValue(2)
    dialog.scale_percent.setValue(30)
    dialog.color_count.setValue(1)
    dialog.color_percent.setValue(10)

    assert dialog.settings() == VariationSettings(
        rotation_count=1,
        rotation_degrees=45.0,
        flip_horizontal=True,
        flip_vertical=False,
        scale_count=2,
        scale_percent=30.0,
        color_count=1,
        color_percent=10.0,
    )


def test_buttons_are_extend_and_cancel(dialog):
    texts = [button.text() for button in dialog.findChildren(QPushButton)]

    assert "Utöka" in texts
    assert "Avbryt" in texts


def test_extend_button_accepts_the_dialog(dialog):
    dialog.rotation_count.setValue(1)

    dialog.extend_button.click()

    assert dialog.result() == QDialog.DialogCode.Accepted


def test_cancel_button_rejects_the_dialog(dialog):
    dialog.rotation_count.setValue(1)
    cancel = next(
        button for button in dialog.findChildren(QPushButton) if button.text() == "Avbryt"
    )

    cancel.click()

    assert dialog.result() == QDialog.DialogCode.Rejected


def test_summary_follows_the_counts_down_again(dialog):
    dialog.scale_count.setValue(4)
    assert dialog.extend_button.isEnabled()

    dialog.scale_count.setValue(0)

    assert dialog.summary.text() == NO_VARIATIONS
    assert not dialog.extend_button.isEnabled()
