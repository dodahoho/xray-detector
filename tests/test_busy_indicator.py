"""Upptagenindikatorn som egen komponent (TASK-40)."""

import time

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

from xray_detector.ui.busy_indicator import BusyIndicator


def _spin_until(qapp, predicate, timeout_s: float = 2.0) -> bool:
    """Kör händelseloopen tills villkoret är uppfyllt eller tiden tar slut."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        qapp.processEvents()
        time.sleep(0.005)
    return predicate()


@pytest.fixture
def parent(qapp) -> QWidget:
    widget = QWidget()
    widget.resize(400, 300)
    return widget


def test_indicator_is_idle_until_started(qapp, parent):
    indicator = BusyIndicator(parent, delay_ms=10)

    assert not indicator.is_busy()
    assert not indicator.is_revealed()


def test_indicator_waits_for_the_delay_before_showing(qapp, parent):
    indicator = BusyIndicator(parent, delay_ms=200)

    indicator.start("Laddar modell...")

    assert indicator.is_busy()
    assert not indicator.is_revealed(), "fördröjningen ska hindra en blinkning"
    assert _spin_until(qapp, indicator.is_revealed)
    assert indicator.text() == "Laddar modell..."


def test_fast_operation_never_reveals_the_indicator(qapp, parent):
    indicator = BusyIndicator(parent, delay_ms=200)

    indicator.start("Snabb operation")
    indicator.stop()

    assert not _spin_until(qapp, indicator.is_revealed, timeout_s=0.3)
    assert not indicator.is_busy()


def test_spinner_animates_while_revealed(qapp, parent):
    indicator = BusyIndicator(parent, delay_ms=1)
    indicator.start()
    assert _spin_until(qapp, indicator.is_revealed)

    start_angle = indicator.angle()

    assert _spin_until(qapp, lambda: indicator.angle() != start_angle)


def test_stop_hides_the_indicator(qapp, parent):
    indicator = BusyIndicator(parent, delay_ms=1)
    indicator.start()
    assert _spin_until(qapp, indicator.is_revealed)

    indicator.stop()

    assert not indicator.is_busy()
    assert not indicator.is_revealed()


def test_indicator_covers_its_parent(qapp, parent):
    indicator = BusyIndicator(parent, delay_ms=1)
    indicator.start()
    assert _spin_until(qapp, indicator.is_revealed)
    assert indicator.geometry() == parent.rect()

    # Qt skickar resize-händelsen först när widgeten syns, som i appen
    parent.show()
    qapp.processEvents()
    parent.resize(640, 480)
    qapp.processEvents()

    assert indicator.geometry() == parent.rect()
    parent.hide()


def test_indicator_paints_spinner_and_text(qapp, parent):
    indicator = BusyIndicator(parent, delay_ms=1)
    indicator.start("Sparar annoteringar...")
    assert _spin_until(qapp, indicator.is_revealed)

    pixmap = QPixmap(indicator.size())
    indicator.render(pixmap)

    assert pixmap.size() == QSize(400, 300)
