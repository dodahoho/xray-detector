from dataclasses import dataclass

import numpy as np


@dataclass
class AnnotatedImage:
    frame: np.ndarray
    annotations: list[dict]


@dataclass(frozen=True)
class VariationSettings:
    """Hur många syntetiska variationer varje originalbild ska få (TASK-88).

    Antalet gäller per bild, så ett bildpar får samma antal variationer och
    varje variation blir ett eget bildpar. Vändningen har inget antal: de två
    riktningarna är var sin variation. Styrkan är den största förändringen,
    så rotation 30 ger en vinkel i intervallet -30 till 30 grader.
    """

    rotation_count: int = 0
    rotation_degrees: float = 0.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    scale_count: int = 0
    scale_percent: float = 0.0
    color_count: int = 0
    color_percent: float = 0.0

    @property
    def flip_count(self) -> int:
        """Antal vändningar: en per vald riktning."""
        return int(self.flip_horizontal) + int(self.flip_vertical)

    @property
    def total(self) -> int:
        """Antal variationer som varje originalbild får."""
        return (
            self.rotation_count
            + self.flip_count
            + self.scale_count
            + self.color_count
        )
