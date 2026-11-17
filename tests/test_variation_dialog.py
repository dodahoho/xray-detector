"""Dialogen för att utöka datasetet med bildvariationer (TASK-88, TASK-106, TASK-117)."""

import pytest
from PySide6.QtWidgets import QDialog, QPushButton

from xray_detector.domain.dataset import (
    MODE_ALL,
    MODE_PER_TYPE,
    MODE_RANDOM,
    MODES,
    VariationSettings,
)
from xray_detector.ui.variation_dialog import (
    MAX_SCALE_DOWN_PERCENT,
    MAX_SCALE_UP_PERCENT,
    NO_VARIATIONS,
    VariationDialog,
)


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
        scale_up_percent=50.0,
        scale_down_percent=50.0,
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
        "En bild per variationstyp ger 3 nya bildpar från 3 original."
    )


def test_the_count_sets_the_number_of_variations_per_pair(dialog):
    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(MODE_ALL))
    dialog.rotation.setChecked(True)
    dialog.count.setValue(5)

    assert dialog.settings().total == 5
    assert dialog.summary.text().startswith("5 variationer per bildpar")


def test_the_count_is_a_sub_option_to_the_combination(dialog):
    """Antalet gäller bara när en bild får flera typer (TASK-117)."""
    assert not dialog.count_row.isEnabled()
    assert not dialog.count.isEnabled()

    for mode in (MODE_ALL, MODE_RANDOM):
        dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(mode))

        assert dialog.count_row.isEnabled()
        assert dialog.count.isEnabled()

    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(MODE_PER_TYPE))

    assert not dialog.count_row.isEnabled()


def test_per_type_gives_one_image_per_active_type(dialog):
    """En bild per variationstyp ger en bild per vald typ, oavsett antalet (TASK-117)."""
    dialog.count.setValue(7)
    dialog.rotation.setChecked(True)
    dialog.flip.setChecked(True)
    dialog.scale.setChecked(True)

    assert dialog.settings().total == 3
    assert dialog.summary.text() == (
        "En bild per variationstyp ger 9 nya bildpar från 3 original."
    )


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
    dialog.scale_up_percent.setValue(30)
    dialog.scale_down_percent.setValue(10)
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
        scale_up_percent=30.0,
        scale_down_percent=10.0,
        color=True,
        color_percent=10.0,
    )


def test_the_scale_has_separate_limits_for_growing_and_shrinking(dialog):
    """En bild kan växa mer än den kan krympa, som annars blir noll (TASK-117)."""
    assert dialog.scale_up_percent.maximum() == MAX_SCALE_UP_PERCENT
    assert dialog.scale_down_percent.maximum() == MAX_SCALE_DOWN_PERCENT
    assert MAX_SCALE_UP_PERCENT > 100
    assert MAX_SCALE_DOWN_PERCENT < 100


def test_the_mode_combo_offers_the_three_combinations(dialog):
    modes = [
        dialog.mode_combo.itemData(index)
        for index in range(dialog.mode_combo.count())
    ]

    assert modes == [MODE_PER_TYPE, MODE_ALL, MODE_RANDOM]


def test_the_mode_labels_are_shortened(dialog):
    labels = [
        dialog.mode_combo.itemText(index)
        for index in range(dialog.mode_combo.count())
    ]

    assert labels == [
        "En per variationstyp",
        "Alla valda variationer",
        "Slumpvisa kombinationer",
    ]
    assert list(MODES.values()) == labels


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
