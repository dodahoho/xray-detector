"""Avslutet när fönstret har stängts (TASK-175)."""

import logging

from xray_detector import app as app_module


class _Pool:
    """Trådpool som svarar med ett förutbestämt resultat."""

    def __init__(self, done: bool) -> None:
        self.done = done
        self.timeouts: list[int] = []

    def waitForDone(self, timeout_ms: int) -> bool:
        self.timeouts.append(timeout_ms)
        return self.done


def _patch(monkeypatch, pool):
    exits: list[int] = []
    monkeypatch.setattr(app_module.QThreadPool, "globalInstance", lambda: pool)
    monkeypatch.setattr(app_module.logging, "shutdown", lambda: None)
    monkeypatch.setattr(app_module.os, "_exit", exits.append)
    return exits


def test_finish_exits_when_the_thread_pool_is_done(monkeypatch, caplog):
    pool = _Pool(done=True)
    exits = _patch(monkeypatch, pool)

    with caplog.at_level(logging.INFO):
        app_module._finish(0, logging.getLogger("xray"))

    assert exits == [0]
    assert pool.timeouts == [app_module.SHUTDOWN_TIMEOUT_MS]
    assert "Avslutar: stänger processen" in caplog.text


def test_finish_exits_and_warns_when_the_thread_pool_hangs(monkeypatch, caplog):
    """En trådpool som aldrig blir klar får inte hålla kvar processen."""
    pool = _Pool(done=False)
    exits = _patch(monkeypatch, pool)

    with caplog.at_level(logging.WARNING):
        app_module._finish(3, logging.getLogger("xray"))

    assert exits == [3]
    assert "Trådpoolen blev inte klar" in caplog.text
