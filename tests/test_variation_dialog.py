"""Dialogen för att utöka datasetet med bildvariationer (TASK-88, TASK-106)."""

import pytest
from PySide6.QtWidgets import QDialog, QPushButton

from xray_detector.domain.dataset import (
    MODE_ALL,
    MODE_PER_TYPE,
    MODE_RANDOM,
    VariationSettings,
)
from xray_detector.ui.variation_dialog import NO_VARIATIONS, VariationDialog


@pytest.fixture
def dialog(qapp) -> VariationDialog:
    return VariationDialog(3)


def test_dialog_starts_without_an_active_type(dialog):
    """Inget händer förrän användaren aktiverar en variationstyp."""
    assert dialog.settings() == VariationSettings(
        count=1,
        mode=MODE_PER_TYPE,
        rotation=False,
        rotation_degrees=360.0,
        flip_horizontal=False,
        flip_vertical=False,
        scale=False,
        scale_percent=50.0,
        color=False,
        color_percent=20.0,
    )
    assert dialog.summary.text() == NO_VARIATIONS
    assert not dialog.extend_button.isEnabled()


def test_dialog_is_titled_after_the_button(dialog):
    assert dialog.windowTitle() == "Utöka med bildvariationer"


def test_an_active_type_enables_the_extend_button(dialog):
    dialog.rotation.setChecked(True)

    assert dialog.extend_button.isEnabled()
    assert dialog.summary.text() == (
        "1 syntetiska bilder per bildpar ger 3 nya bildpar från 3 original."
    )


def test_the_count_sets_the_number_of_images_per_pair(dialog):
    dialog.rotation.setChecked(True)
    dialog.count.setValue(5)

    assert dialog.settings().total == 5
    assert dialog.summary.text().startswith("5 syntetiska bilder per bildpar")


def test_a_type_card_disables_its_fields_until_it_is_checked(dialog):
    """Rotationens vinkel går bara att ställa in när rotationen är vald (TASK-106)."""
    assert not dialog.rotation_degrees.isEnabled()

    dialog.rotation.setChecked(True)

    assert dialog.rotation_degrees.isEnabled()


def test_the_flip_directions_need_the_flip_card(dialog):
    """Vändningen aktiveras av sitt kort, inte av riktningarna i sig (TASK-106)."""
    assert dialog.flip_horizontal.isChecked()
    assert dialog.settings().flip_count == 0

    dialog.flip.setChecked(True)

    assert dialog.settings().flip_count == 2


def test_settings_reads_every_field(dialog):
    dialog.count.setValue(4)
    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(MODE_ALL))
    dialog.rotation.setChecked(True)
    dialog.rotation_degrees.setValue(45)
    dialog.flip.setChecked(True)
    dialog.flip_vertical.setChecked(False)
    dialog.scale.setChecked(True)
    dialog.scale_percent.setValue(30)
    dialog.color.setChecked(True)
    dialog.color_percent.setValue(10)

    assert dialog.settings() == VariationSettings(
        count=4,
        mode=MODE_ALL,
        rotation=True,
        rotation_degrees=45.0,
        flip_horizontal=True,
        flip_vertical=False,
        scale=True,
        scale_percent=30.0,
        color=True,
        color_percent=10.0,
    )


def test_the_mode_combo_offers_the_three_combinations(dialog):
    modes = [
        dialog.mode_combo.itemData(index)
        for index in range(dialog.mode_combo.count())
    ]

    assert modes == [MODE_PER_TYPE, MODE_ALL, MODE_RANDOM]


def test_buttons_are_extend_and_cancel(dialog):
    texts = [button.text() for button in dialog.findChildren(QPushButton)]

    assert "Utöka" in texts
    assert "Avbryt" in texts


def test_extend_button_accepts_the_dialog(dialog):
    dialog.rotation.setChecked(True)

    dialog.extend_button.click()

    assert dialog.result() == QDialog.DialogCode.Accepted


def test_cancel_button_rejects_the_dialog(dialog):
    dialog.rotation.setChecked(True)
    cancel = next(
        button for button in dialog.findChildren(QPushButton) if button.text() == "Avbryt"
    )

    cancel.click()

    assert dialog.result() == QDialog.DialogCode.Rejected


def test_summary_follows_the_type_choice_down_again(dialog):
    dialog.scale.setChecked(True)
    assert dialog.extend_button.isEnabled()

    dialog.scale.setChecked(False)

    assert dialog.summary.text() == NO_VARIATIONS
    assert not dialog.extend_button.isEnabled()
