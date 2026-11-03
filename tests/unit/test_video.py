from __future__ import annotations

import cv2
import numpy as np

from xray_detector.infrastructure.video.frame_buffer import FrameBuffer
from xray_detector.infrastructure.video.source import (
    SourceSpec,
    SyntheticVideoSource,
    create_source,
)


def test_test_pattern_source_produces_frames():
    spec = SourceSpec(role="cam0", type="test_pattern", width=320, height=240, fps=30)
    source = create_source(spec)
    assert isinstance(source, SyntheticVideoSource)
    source.open()
    first = source.read()
    second = source.read()
    source.close()

    assert first is not None and second is not None
    assert first.shape == (240, 320, 3)
    assert first.dtype == np.uint8
    assert not np.array_equal(first, second)


def test_frame_buffer_sequence_and_snapshot(frame):
    buffer = FrameBuffer("cam0")
    first = buffer.update(frame, 1.0)
    second = buffer.update(frame, 2.0)
    assert first.sequence == 1
    assert second.sequence == 2
    snapshot = buffer.snapshot()
    assert snapshot is not None
    assert snapshot.sequence == 2
    snapshot.frame[:] = 255
    assert buffer.latest().frame.max() < 255


def test_file_source_reads_and_loops(tmp_path):
    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    if not writer.isOpened():
        return
    for index in range(3):
        writer.write(np.full((48, 64, 3), index * 20, dtype=np.uint8))
    writer.release()

    spec = SourceSpec(role="cam0", type="file", file=str(path), loop_file=False)
    source = create_source(spec)
    source.open()
    frames = [source.read() for _ in range(3)]
    assert all(item is not None for item in frames)
    assert source.read() is None
    assert source.at_end
    source.close()

    looping = create_source(SourceSpec(role="cam0", type="file", file=str(path), loop_file=True))
    looping.open()
    for _ in range(5):
        assert looping.read() is not None
    looping.close()
