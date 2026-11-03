from __future__ import annotations

from xray_detector.dataset.pending import (
    delete_pending_capture,
    list_pending_captures,
    load_pending_capture,
)


def test_pending_capture_roundtrip(paths, capture_factory) -> None:
    capture = capture_factory(3)
    assert capture.image_path("left").exists()
    assert capture.image_path("right").exists()
    loaded = load_pending_capture(capture.directory)
    assert loaded.group_id == capture.group_id
    assert set(loaded.images) == {"left", "right"}
    assert loaded.images["left"].detections[0].class_name == "skruv"
    assert len(list_pending_captures(paths.pending)) == 1
    delete_pending_capture(capture)
    assert list_pending_captures(paths.pending) == []
