from pathlib import Path

from xray_detector.infrastructure.detectors.base import BaseDetector
from xray_detector.infrastructure.video.camera_service import CameraService
from xray_detector.infrastructure.video.devices import DeviceInfo, list_devices
from xray_detector.infrastructure.video.source import FileSource, UvcSource, VideoSource


class VideoService:
    """Bygger videokällor och delegerar till kameratrådarna."""

    def __init__(self) -> None:
        self.camera_service = CameraService()

    @staticmethod
    def list_devices() -> list[DeviceInfo]:
        """Tillgängliga UVC-enheter med namn (pygrabber) eller indexfallback."""
        return list_devices()

    def set_source(self, source_id: str, kind: str, value: object):
        source: VideoSource | None = None
        if kind == "uvc" and value is not None:
            source = UvcSource(int(value))
        elif kind == "file" and value:
            source = FileSource(Path(value))
        return self.camera_service.set_source(source_id, source)

    def set_detector(self, detector: BaseDetector | None) -> None:
        self.camera_service.set_detector(detector)

    def stop_source(self, source_id: str) -> None:
        self.camera_service.stop_source(source_id)

    def stop_all(self) -> None:
        self.camera_service.stop_all()
