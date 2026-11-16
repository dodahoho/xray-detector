"""Förlopp inom pågående epok (TASK-96).

Epokeventet kommer först när epoken är klar, så en epok som tar flera minuter
ser ut som en hängning. Den här modulen skriver en ``PROGRESS {json}``-rad med
jämna mellanrum under epoken, i linje med ``EPOCH``-raden, så träningsvyn
slipper tolka fri text.

Skrivningarna är throttlade: en rad per batch hade varit ren I/O utan att
tillföra något, eftersom vyn ändå bara hinner rita några gånger i sekunden.
"""

import json
import time

from xray_detector.domain.training import ProgressEvent

PROGRESS_MARKER = "PROGRESS "
DEFAULT_INTERVAL_S = 2.0


def progress_line(event: ProgressEvent) -> str:
    """Rad som beskriver hur långt epoken kommit."""
    return f"{PROGRESS_MARKER}{json.dumps(event.as_dict())}"


def parse_progress_line(line: str) -> ProgressEvent | None:
    """Parsar en ``PROGRESS {json}``-rad; annat innehåll ger None."""
    if not line.startswith(PROGRESS_MARKER):
        return None
    try:
        return ProgressEvent.from_dict(json.loads(line.removeprefix(PROGRESS_MARKER)))
    except (ValueError, KeyError, TypeError):
        return None


class ProgressReporter:
    """Skickar förloppsevent under epoken, högst en gång per intervall.

    En ny epok rapporteras alltid, liksom epokens sista steg, så vyn ser att
    epoken är klar även om den sista batchen kommer inom samma intervall.
    """

    def __init__(self, interval: float = DEFAULT_INTERVAL_S, clock=time.time, emit=None) -> None:
        self.interval = float(interval)
        self._clock = clock
        self._emit = emit if emit is not None else _print_line
        self._last_write = 0.0
        self._last_epoch: int | None = None

    def update(
        self,
        epoch: int,
        step: int,
        total_steps: int,
        force: bool = False,
    ) -> ProgressEvent | None:
        """Rapporterar steget; None när det throttlas bort."""
        now = self._clock()
        if (
            not force
            and epoch == self._last_epoch
            and now - self._last_write < self.interval
        ):
            return None
        self._last_epoch = int(epoch)
        self._last_write = now
        event = ProgressEvent(
            epoch=int(epoch),
            step=int(step),
            total_steps=int(total_steps),
            updated=now,
        )
        self._emit(progress_line(event))
        return event


def _print_line(line: str) -> None:
    print(line, flush=True)
