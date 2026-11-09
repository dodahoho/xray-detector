"""Kraschsäker pending-kö på disk vid bildfångst (TASK-12).

Så fort användaren trycker Fånga sparas råbilderna och detektionerna på
disk under datakatalogens pending/ innan annoteringsvyn öppnas. Kraschar
appen under annoteringen går fångsten inte förlorad: pending-gruppen
listas i datasetvyn vid nästa start och kan annoteras klart eller
raderas. Först när annoteringen sparats (commit till datasetet) tas
pending-gruppen bort.
"""

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json

PENDING_INDEX = "pending.json"


@dataclass
class PendingCapture:
    group_id: str
    directory: Path
    frames: list[StreamFrame]


def pending_root(data_dir: Path) -> Path:
    return Path(data_dir) / "pending"


def save_pending(data_dir: Path, frames: list[StreamFrame]) -> str:
    """Sparar fångstens ramar och detektioner atomärt; returnerar grupp-id."""
    group_id = f"{int(time.time() * 1000):013d}"
    group_dir = pending_root(data_dir) / group_id
    group_dir.mkdir(parents=True, exist_ok=True)
    payload = []
    for index, stream_frame in enumerate(frames, start=1):
        if stream_frame.frame is None:
            continue
        file_name = f"frame_{index:02d}.png"
        cv2.imwrite(str(group_dir / file_name), stream_frame.frame)
        payload.append(
            {
                "file": file_name,
                "source_id": stream_frame.source_id,
                "source_label": stream_frame.source_label,
                "detections": [
                    {
                        "x1": detection.x1,
                        "y1": detection.y1,
                        "x2": detection.x2,
                        "y2": detection.y2,
                        "class_name": detection.class_name,
                        "confidence": detection.confidence,
                    }
                    for detection in stream_frame.detections
                ],
            }
        )
    atomic_write_json(
        group_dir / PENDING_INDEX,
        {
            "group": group_id,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "frames": payload,
        },
    )
    return group_id


def _load_group(group_dir: Path) -> PendingCapture | None:
    index_path = group_dir / PENDING_INDEX
    if not index_path.exists():
        return None
    try:
        with open(index_path, encoding="utf-8") as file:
            index = json.load(file)
        frames = []
        for entry in index.get("frames", []):
            frame = cv2.imread(str(group_dir / entry["file"]))
            if frame is None:
                continue
            detections = [
                Detection(
                    x1=float(d["x1"]),
                    y1=float(d["y1"]),
                    x2=float(d["x2"]),
                    y2=float(d["y2"]),
                    class_name=str(d["class_name"]),
                    confidence=float(d.get("confidence", 1.0)),
                )
                for d in entry.get("detections", [])
            ]
            frames.append(
                StreamFrame(
                    source_id=str(entry.get("source_id", "")),
                    frame=frame,
                    detections=detections,
                    source_label=str(entry.get("source_label", "")),
                )
            )
        if not frames:
            return None
        return PendingCapture(
            group_id=str(index.get("group", group_dir.name)),
            directory=group_dir,
            frames=frames,
        )
    except (OSError, ValueError, KeyError):
        return None


def list_pending(data_dir: Path) -> list[PendingCapture]:
    """Alla osparkade fångster, nyaste först."""
    root = pending_root(data_dir)
    if not root.exists():
        return []
    captures = []
    for group_dir in root.iterdir():
        if group_dir.is_dir():
            capture = _load_group(group_dir)
            if capture is not None:
                captures.append(capture)
    captures.sort(key=lambda capture: capture.group_id, reverse=True)
    return captures


def remove_pending(data_dir: Path, group_id: str) -> None:
    """Tar bort en pending-grupp (efter sparad annotering eller radering)."""
    group_dir = pending_root(data_dir) / group_id
    if group_dir.exists():
        shutil.rmtree(group_dir, ignore_errors=True)
