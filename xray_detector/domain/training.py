from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrainConfig:
    dataset_yaml: Path
    weights: str
    output_dir: Path
    epochs: int = 100
    imgsz: int = 640
    batch: int = 16
