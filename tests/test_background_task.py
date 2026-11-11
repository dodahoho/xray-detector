"""Arbete i trådpoolen med resultatet tillbaka i GUI-tråden (TASK-40)."""

import threading

from PySide6.QtCore import QObject

from xray_detector.application.background_task import BackgroundTask


class _Recorder(QObject):
    """Tar emot signalerna som en QObject-mottagare, alltså i sin egen tråd."""

    def __init__(self) -> None:
        super().__init__()
        self.values = []
        self.threads = []

    def on_succeeded(self, value) -> None:
        self.values.append(value)
        self.threads.append(threading.get_ident())


def test_result_is_delivered_in_the_gui_thread(qapp):
    recorder = _Recorder()
    worker_threads = []

    def work():
        worker_threads.append(threading.get_ident())
        return "klart"

    task = BackgroundTask(work)
    task.succeeded.connect(recorder.on_succeeded)
    task.start()

    assert task.wait(5000)
    assert recorder.values == ["klart"]
    assert worker_threads and worker_threads[0] != threading.get_ident()
    assert recorder.threads == [threading.get_ident()]


def test_exception_becomes_a_message(qapp):
    messages = []

    def work():
        raise RuntimeError("trasig modell")

    task = BackgroundTask(work)
    task.failed.connect(messages.append)
    task.start()

    assert task.wait(5000)
    assert messages == ["trasig modell"]


def test_finished_is_emitted_after_the_result(qapp):
    order = []

    def work():
        return 1

    task = BackgroundTask(work)
    task.succeeded.connect(lambda _value: order.append("succeeded"))
    task.finished.connect(lambda: order.append("finished"))
    task.start()

    assert task.wait(5000)
    assert order == ["succeeded", "finished"]
