"""Gemensamma GUI-mått: alla knappar har samma höjd (TASK-49)."""

import pytest
from PySide6.QtWidgets import QDialogButtonBox, QPushButton

from xray_detector.domain.config import AppConfig
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.settings_dialog import SettingsDialog
from xray_detector.ui.style import (
    BUTTON_HEIGHT,
    ICON_BUTTON_WIDTH,
    apply_metrics,
    button,
)


@pytest.fixture
def window(qapp, tmp_path):
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    yield window
    window.detection_view.wait_for_background()
    window.close()


def test_every_button_in_every_view_has_the_standard_height(window):
    views = (
        window.detection_view,
        window.annotation_view,
        window.dataset_view,
        window.training_view,
        window.settings_view,
    )
    for view in views:
        for widget in view.findChildren(QPushButton):
            assert widget.minimumHeight() == BUTTON_HEIGHT, (
                type(view).__name__,
                widget.text(),
            )
            assert widget.maximumHeight() == BUTTON_HEIGHT, (
                type(view).__name__,
                widget.text(),
            )


def test_training_start_button_is_as_high_as_abort(window):
    start = window.training_view.start_button
    abort = window.training_view.abort_button

    assert start.minimumHeight() == abort.minimumHeight() == BUTTON_HEIGHT
    assert start.maximumHeight() == abort.maximumHeight() == BUTTON_HEIGHT


def test_primary_button_is_emphasized_without_growing(window):
    start = window.training_view.start_button
    abort = window.training_view.abort_button

    assert start.font().bold()
    assert not abort.font().bold()
    assert start.minimumHeight() == abort.minimumHeight() == BUTTON_HEIGHT


def test_class_buttons_keep_their_square_width(window):
    for widget in (
        window.annotation_view.add_class_button,
        window.annotation_view.remove_class_button,
    ):
        assert widget.minimumWidth() == widget.maximumWidth() == ICON_BUTTON_WIDTH


def test_settings_dialog_close_button_uses_the_standard_height(qapp, window):
    dialog = SettingsDialog("Test", [], window)
    close = dialog.findChild(QDialogButtonBox).button(
        QDialogButtonBox.StandardButton.Close
    )

    assert close.minimumHeight() == close.maximumHeight() == BUTTON_HEIGHT


def test_button_accepts_its_own_metrics(qapp):
    tall = button("Hög", height=48)
    assert tall.minimumHeight() == tall.maximumHeight() == 48

    free = button("Fri", height=None)
    assert free.minimumHeight() == 0


def test_apply_metrics_leaves_untouched_measures_to_qt(qapp):
    widget = QPushButton("Stäng")

    apply_metrics(widget, width=80)

    assert widget.minimumHeight() == widget.maximumHeight() == BUTTON_HEIGHT
    assert widget.minimumWidth() == widget.maximumWidth() == 80


def test_rendered_heights_match_when_the_window_is_shown(qapp, window):
    window.show()
    qapp.processEvents()

    training = window.training_view
    assert training.start_button.height() == BUTTON_HEIGHT
    assert training.abort_button.height() == BUTTON_HEIGHT
    assert window.detection_view.capture_button.height() == BUTTON_HEIGHT
    assert window.annotation_view.save_button.height() == BUTTON_HEIGHT
