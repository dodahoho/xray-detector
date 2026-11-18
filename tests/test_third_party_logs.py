"""Tredjepartens varningar och loggrader i app.log (TASK-98)."""

import logging
import re
import warnings

import pytest

from xray_detector.application.app_config import setup_logging
from xray_detector.infrastructure.logging import capture_third_party_logs

DINOV2_WARNING = (
    "Using a different number of positional encodings than DINOv2, which means "
    "we're not loading DINOv2 backbone weights."
)


@pytest.fixture
def app_log(tmp_path):
    """Rotationsloggen i en tmp-katalog, utan rot-handlers från andra tester."""
    root = logging.getLogger()
    before = list(root.handlers)
    setup_logging(tmp_path / "logs")
    yield tmp_path / "logs" / "app.log"
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)
            handler.close()


def _content(path) -> str:
    for handler in logging.getLogger().handlers:
        handler.flush()
    return path.read_text(encoding="utf-8")


def test_warning_during_run_lands_in_app_log_with_timestamp(app_log):
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        warnings.warn("tredjepartsvarning 4711", stacklevel=2)

    content = _content(app_log)
    assert "tredjepartsvarning 4711" in content
    # tidsstämpel, process-id, nivå och loggerns namn, som appens egna rader
    assert re.search(
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \[\d+\] WARNING py\.warnings: ",
        content,
        re.MULTILINE,
    )


def test_third_party_rows_are_distinguishable_from_app_rows(app_log):
    logging.getLogger("rfdetr.models.lwdetr").warning("rfdetr-varning 12")
    logging.getLogger("xray").info("appens egen rad 34")

    content = _content(app_log)
    assert "WARNING rfdetr.models.lwdetr: rfdetr-varning 12" in content
    assert "INFO xray: appens egen rad 34" in content


def test_comtypes_noise_stays_out_of_app_log(app_log):
    noisy = logging.getLogger("comtypes.client._code_cache")
    noisy.info("comtypes-brus 56")
    noisy.warning("comtypes-varning 78")

    content = _content(app_log)
    assert "comtypes-brus 56" not in content
    # nivåstyrning, inte tystnad: riktiga problem från samma logger syns
    assert "comtypes-varning 78" in content


def test_rfdetr_logger_is_led_into_app_log(app_log):
    logger = logging.getLogger("rfdetr.testmodul")
    logger.propagate = False
    logger.addHandler(logging.NullHandler())
    try:
        capture_third_party_logs()
        assert logger.propagate is True
        logger.warning("rfdetr-rad 90")
        assert "rfdetr-rad 90" in _content(app_log)
    finally:
        logger.handlers.clear()


def test_dinov2_warning_remains_a_signal(app_log):
    """TASK-36 lämnade DINOv2-varningen som signal; den ska nu även nå filen."""
    logging.getLogger("rf-detr").warning(DINOV2_WARNING)

    content = _content(app_log)
    assert DINOV2_WARNING in content
    assert "WARNING rf-detr:" in content


def test_rfdetr_import_triggers_capture(monkeypatch):
    """rfdetr skapar sina loggrar först vid import, så fångsten görs om där."""
    import sys
    import types

    from xray_detector.infrastructure.detectors import rfdetr_detector

    fake = types.ModuleType("rfdetr")
    fake.RFDETRSmall = type("RFDETRSmall", (), {})
    monkeypatch.setitem(sys.modules, "rfdetr", fake)

    logger = logging.getLogger("rfdetr.models.sent")
    logger.propagate = False
    rfdetr_detector.rfdetr_variant("rfdetr-small")
    assert logger.propagate is True
