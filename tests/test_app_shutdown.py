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


class _Thread:
    """Vakt-tråd som bara minns hur den startades."""

    def __init__(self, target, args, daemon) -> None:
        self.started = (target, args, daemon)

    def start(self) -> None:
        pass


def _patch(monkeypatch, pool):
    started: list[tuple] = []

    def thread(target, args, daemon):
        thread.started = (target, args, daemon)
        started.append(thread.started)
        return _Thread(target, args, daemon)

    monkeypatch.setattr(app_module.QThreadPool, "globalInstance", lambda: pool)
    monkeypatch.setattr(app_module.logging, "shutdown", lambda: None)
    monkeypatch.setattr(app_module.threading, "Thread", thread)
    return started


def test_finish_starts_the_watchdog_when_the_thread_pool_is_done(monkeypatch, caplog):
    pool = _Pool(done=True)
    started = _patch(monkeypatch, pool)

    with caplog.at_level(logging.INFO):
        app_module._finish(0, logging.getLogger("xray"))

    assert pool.timeouts == [app_module.SHUTDOWN_TIMEOUT_MS]
    assert started == [(app_module._force_exit, (0,), True)]
    assert "Avslutar: stänger processen" in caplog.text


def test_finish_warns_when_the_thread_pool_hangs(monkeypatch, caplog):
    """En trådpool som aldrig blir klar får inte hålla kvar processen."""
    pool = _Pool(done=False)
    started = _patch(monkeypatch, pool)

    with caplog.at_level(logging.WARNING):
        app_module._finish(3, logging.getLogger("xray"))

    assert started == [(app_module._force_exit, (3,), True)]
    assert "Trådpoolen blev inte klar" in caplog.text


def test_force_exit_terminates_the_process(monkeypatch):
    exits: list[int] = []
    monkeypatch.setattr(app_module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(app_module.os, "_exit", exits.append)

    app_module._force_exit(3)

    assert exits == [3]
