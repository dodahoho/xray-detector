"""Epokvisa träningsvärden ur träningsprocessens metrics-filer (TASK-44).

Ultralytics skriver ``results.csv`` och RF-DETR ``metrics.csv``, en rad per
loggning. Modulen läser de rader som tillkommit sedan förra läsningen, bygger
ett :class:`EpochMetrics` per epok och skickar det som en ``EPOCH {json}``-rad
på stdout. GUI:t parsar raden i stället för att tolka fri text, och slipper
bry sig om vilken familj som tränar.
"""

import csv
import json
import math
import threading
from pathlib import Path

from xray_detector.domain.training import EpochMetrics

EPOCH_MARKER = "EPOCH "
ABORT_MARKER = "ABORT "
POLL_INTERVAL_S = 0.5

#: RF-DETR:s kolumnnamn i metrics.csv (PyTorch Lightnings CSVLogger).
RFDETR_COLUMNS = {
    "train_loss": "train/loss",
    "val_loss": "val/loss",
    "map50": "val/mAP_50",
    "map50_95": "val/mAP_50_95",
    "precision": "val/precision",
    "recall": "val/recall",
}

#: YOLO:s kolumnnamn i results.csv.
YOLO_COLUMNS = {
    "map50": "metrics/mAP50(B)",
    "map50_95": "metrics/mAP50-95(B)",
    "precision": "metrics/precision(B)",
    "recall": "metrics/recall(B)",
}


def _number(value) -> float | None:
    """Tal ur en CSV-cell; tomt, text och NaN blir None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def _loss(row: dict, prefix: str) -> float | None:
    """Summan av radens förlustkolumner med givet prefix.

    YOLO delar upp förlusten i box/cls/dfl, så en enda train-loss är summan
    av delarna. RF-DETR har redan en kolumn, som då blir summan av sig själv.
    """
    values = []
    for column, value in row.items():
        if not column or not column.startswith(prefix) or not column.endswith("loss"):
            continue
        number = _number(value)
        if number is not None:
            values.append(number)
    return sum(values) if values else None


def parse_yolo_row(row: dict, total_epochs: int) -> EpochMetrics | None:
    """En rad ur ultralytics results.csv; epokkolumnen är ettabaserad."""
    epoch = _number(row.get("epoch"))
    if epoch is None:
        return None
    return EpochMetrics(
        epoch=int(epoch),
        total_epochs=total_epochs,
        train_loss=_loss(row, "train/"),
        val_loss=_loss(row, "val/"),
        map50=_number(row.get(YOLO_COLUMNS["map50"])),
        map50_95=_number(row.get(YOLO_COLUMNS["map50_95"])),
        precision=_number(row.get(YOLO_COLUMNS["precision"])),
        recall=_number(row.get(YOLO_COLUMNS["recall"])),
    )


def parse_rfdetr_row(row: dict, total_epochs: int) -> EpochMetrics | None:
    """En rad ur RF-DETR:s metrics.csv.

    Lightning skriver en rad per loggning, så train- och valvärdena för samma
    epok kan ligga i olika rader. Raden fyller därför bara i de värden den har.
    """
    epoch = _number(row.get("epoch"))
    if epoch is None:
        return None
    return EpochMetrics(
        epoch=int(epoch) + 1,
        total_epochs=total_epochs,
        **{
            name: _number(row.get(column))
            for name, column in RFDETR_COLUMNS.items()
        },
    )


def parse_event_line(line: str) -> EpochMetrics | None:
    """Parsar en ``EPOCH {json}``-rad; annat innehåll ger None."""
    if not line.startswith(EPOCH_MARKER):
        return None
    try:
        payload = json.loads(line.removeprefix(EPOCH_MARKER))
        return EpochMetrics.from_dict(payload)
    except (ValueError, KeyError, TypeError):
        return None


def abort_line(reason: str) -> str:
    """Rad som talar om varför träningen avbröts (TASK-46)."""
    return f"{ABORT_MARKER}{json.dumps({'reason': reason})}"


def parse_abort_line(line: str) -> str | None:
    """Parsar en ``ABORT {json}``-rad; annat innehåll ger None."""
    if not line.startswith(ABORT_MARKER):
        return None
    try:
        payload = json.loads(line.removeprefix(ABORT_MARKER))
        return str(payload["reason"])
    except (ValueError, KeyError, TypeError):
        return None


def _merge(previous: EpochMetrics | None, current: EpochMetrics) -> EpochMetrics:
    """Slår ihop två ofullständiga rader för samma epok; nya värden vinner."""
    if previous is None:
        return current
    values = {}
    for name in ("train_loss", "val_loss", "map50", "map50_95", "precision", "recall"):
        value = getattr(current, name)
        values[name] = value if value is not None else getattr(previous, name)
    return EpochMetrics(
        epoch=current.epoch, total_epochs=current.total_epochs, **values
    )


def _complete(metrics: EpochMetrics) -> bool:
    """Sant när epoken har både train-loss och något valvärde."""
    has_validation = metrics.map50_95 is not None or metrics.val_loss is not None
    return metrics.train_loss is not None and has_validation


class EpochAccumulator:
    """Bygger ett komplett epokevent ur metrics-raderna.

    YOLO skriver en komplett rad per epok. RF-DETR skriver en rad per
    loggning, så raderna för samma epok slås ihop tills epoken är komplett.
    """

    def __init__(self, family: str, total_epochs: int) -> None:
        self.family = family
        self.total_epochs = total_epochs
        self._pending: dict[int, EpochMetrics] = {}
        self._emitted: set[int] = set()

    def feed(self, row: dict) -> EpochMetrics | None:
        if self.family == "rfdetr":
            return self._feed_rfdetr(row)
        metrics = parse_yolo_row(row, self.total_epochs)
        if metrics is None or metrics.epoch in self._emitted:
            return None
        self._emitted.add(metrics.epoch)
        return metrics

    def _feed_rfdetr(self, row: dict) -> EpochMetrics | None:
        partial = parse_rfdetr_row(row, self.total_epochs)
        if partial is None:
            return None
        merged = _merge(self._pending.get(partial.epoch), partial)
        self._pending[partial.epoch] = merged
        if partial.epoch in self._emitted or not _complete(merged):
            return None
        self._emitted.add(partial.epoch)
        self._pending.pop(partial.epoch, None)
        return merged

    def flush(self) -> list[EpochMetrics]:
        """Epoker som aldrig blev kompletta, i epokordning."""
        remaining = [
            metrics
            for epoch, metrics in sorted(self._pending.items())
            if epoch not in self._emitted
        ]
        self._pending.clear()
        return remaining


class MetricsTail:
    """Läser de rader som tillkommit i en CSV-fil som växer under träningen."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._offset = 0
        self._header: list[str] | None = None
        self._partial = b""

    def read_new_rows(self) -> list[dict[str, str]]:
        try:
            size = self.path.stat().st_size
        except OSError:
            return []
        if size < self._offset:
            # filen skrevs om, t.ex. när Lightning startar en ny körning
            self._offset = 0
            self._header = None
            self._partial = b""
        if size == self._offset:
            return []
        try:
            with open(self.path, "rb") as file:
                file.seek(self._offset)
                chunk = file.read()
                self._offset = file.tell()
        except OSError:
            return []
        lines = (self._partial + chunk).split(b"\n")
        self._partial = lines.pop()
        rows: list[dict[str, str]] = []
        for raw in lines:
            line = raw.decode("utf-8", errors="replace").strip("\r")
            if not line:
                continue
            values = next(csv.reader([line]))
            if self._header is None:
                self._header = values
                continue
            rows.append(dict(zip(self._header, values, strict=False)))
        return rows


class EpochReporter(threading.Thread):
    """Pollar metrics-filen och skickar ett epokevent per epok (TASK-44).

    Tråden är daemon och stängs med stop(); den sista läsningen och de epoker
    som aldrig blev kompletta skickas då också, så en avbruten träning ändå
    rapporterar det som hann bli klart.
    """

    def __init__(
        self,
        path: Path,
        family: str,
        total_epochs: int,
        on_epoch=None,
        interval: float = POLL_INTERVAL_S,
    ) -> None:
        super().__init__(daemon=True, name="epoch-reporter")
        self.path = Path(path)
        self.family = family
        self.total_epochs = total_epochs
        self.on_epoch = on_epoch
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self) -> None:
        tail = MetricsTail(self.path)
        accumulator = EpochAccumulator(self.family, self.total_epochs)
        while not self._stop_event.is_set():
            self._drain(tail, accumulator)
            self._stop_event.wait(self.interval)
        self._drain(tail, accumulator)
        for metrics in accumulator.flush():
            self._emit(metrics)

    def stop(self) -> None:
        self._stop_event.set()

    def _drain(self, tail: MetricsTail, accumulator: EpochAccumulator) -> None:
        for row in tail.read_new_rows():
            metrics = accumulator.feed(row)
            if metrics is not None:
                self._emit(metrics)

    def _emit(self, metrics: EpochMetrics) -> None:
        print(f"{EPOCH_MARKER}{json.dumps(metrics.as_dict())}", flush=True)
        if self.on_epoch is None:
            return
        try:
            self.on_epoch(metrics)
        except Exception as exc:  # noqa: BLE001 - träningen får inte stanna här
            print(f"Varning: epokeventet kunde inte hanteras: {exc}", flush=True)
