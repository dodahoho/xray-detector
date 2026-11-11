"""Kör tidskrävande arbete utanför GUI-tråden (TASK-40).

En indikator som animeras kräver att GUI-tråden är ledig. Den här modulen ger
den lilla byggsten som vyerna använder för att flytta arbetet till trådpoolen
och få tillbaka resultatet i GUI-tråden.
"""

import time
from collections.abc import Callable

from PySide6.QtCore import QCoreApplication, QObject, QRunnable, QThreadPool, Signal

POLL_INTERVAL_S = 0.005
DEFAULT_TIMEOUT_MS = 10000


class BackgroundTask(QObject):
    """Kör en funktion i trådpoolen och levererar resultatet till GUI-tråden.

    Signalerna levereras med köad anslutning till den tråd som äger mottagaren,
    så en vy får alltid resultatet i GUI-tråden. Ett undantag i arbetet blir ett
    felmeddelande i stället för en krasch i arbetstråden.

    Uppgiften har ingen förälder: en vy som rivs medan arbetet pågår får sina
    anslutningar bortkopplade av Qt, och trådpoolen väntar in arbetet vid avslut.
    """

    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, work: Callable[[], object]) -> None:
        super().__init__()
        self._work = work
        self._done = False

    def start(self) -> None:
        QThreadPool.globalInstance().start(_TaskRunnable(self))

    def is_done(self) -> bool:
        return self._done

    def wait(self, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> bool:
        """Väntar tills arbetet är klart och låter resultatet nå GUI-tråden."""
        deadline = time.monotonic() + timeout_ms / 1000
        while not self._done and time.monotonic() < deadline:
            QCoreApplication.processEvents()
            time.sleep(POLL_INTERVAL_S)
        QCoreApplication.processEvents()
        return self._done

    def _run(self) -> None:
        try:
            result = self._work()
        except Exception as exc:  # noqa: BLE001 - felet ska bli ett meddelande
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)
        finally:
            self._done = True
            self.finished.emit()


class _TaskRunnable(QRunnable):
    """Trådpoolens del: kör arbetet och rapporterar på uppgiftens signaler."""

    def __init__(self, task: BackgroundTask) -> None:
        super().__init__()
        self._task = task

    def run(self) -> None:
        self._task._run()
