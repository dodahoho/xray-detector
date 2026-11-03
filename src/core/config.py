from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import yaml


DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "title": "X-ray Detector",
        "kiosk_fullscreen": False,
        "inactivity_timeout_minutes": 30,
        "night_training_window_start": "23:00",
        "night_training_window_end": "05:00",
    },
    "cameras": {
        "stream_1": {
            "device_index": 0,
            "name": "Röntgenström 1 (Vy A)",
            "width": 1280,
            "height": 720,
            "fps": 30,
            "use_dshow": True,
            "fallback_synthetic": True,
        },
        "stream_2": {
            "device_index": 1,
            "name": "Röntgenström 2 (Vy B)",
            "width": 1280,
            "height": 720,
            "fps": 30,
            "use_dshow": True,
            "fallback_synthetic": True,
        },
    },
    "detection": {
        "active_model_family": "YOLO26",
        "active_weights_path": "",
        "confidence_threshold": 0.25,
        "iou_threshold": 0.45,
        "target_fps": 30,
    },
    "dataset": {
        "working_dir": "data/working",
        "exports_dir": "data/datasets",
        "default_classes": [
            "Metallföremål",
            "Batteri",
            "Vätszebehållare",
            "Elektronik",
            "Okänt objekt",
        ],
    },
    "models": {
        "models_dir": "models/trained",
        "base_models": [
            {
                "name": "YOLO26-nano (Basmodell)",
                "family": "YOLO26",
                "weights": "yolo26n.pt",
            },
            {
                "name": "YOLO26-small (Basmodell)",
                "family": "YOLO26",
                "weights": "yolo26s.pt",
            },
            {
                "name": "YOLO11-nano (Basmodell)",
                "family": "YOLO",
                "weights": "yolo11n.pt",
            },
            {
                "name": "RF-DETR-base (Basmodell)",
                "family": "RF-DETR",
                "weights": "rf-detr-base.pth",
            },
            {
                "name": "Simulated X-ray Detector (Snabbtest/Fallback)",
                "family": "SIMULATED",
                "weights": "simulated",
            },
        ],
    },
}


class AppConfig:
    """Hanterar läsning och skrivning av applikationskonfiguration i YAML."""

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            self.data = self._merge_defaults(DEFAULT_CONFIG, loaded)
        else:
            self.data = yaml.safe_load(yaml.dump(DEFAULT_CONFIG))
            self.save()

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.data, f, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _merge_defaults(defaults: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(defaults)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = AppConfig._merge_defaults(result[k], v)
            else:
                result[k] = v
        return result

    @property
    def app(self) -> Dict[str, Any]:
        return self.data["app"]

    @property
    def cameras(self) -> Dict[str, Any]:
        return self.data["cameras"]

    @property
    def detection(self) -> Dict[str, Any]:
        return self.data["detection"]

    @property
    def dataset(self) -> Dict[str, Any]:
        return self.data["dataset"]

    @property
    def models(self) -> Dict[str, Any]:
        return self.data["models"]

    def get_base_models(self) -> List[Dict[str, str]]:
        return self.models.get("base_models", [])
