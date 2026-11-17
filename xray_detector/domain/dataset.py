from dataclasses import dataclass

import numpy as np

# hur de aktiverade variationstyperna kombineras i en syntetisk bild (TASK-106, TASK-117)
MODE_PER_TYPE = "per_type"
MODE_ALL = "all"
MODE_RANDOM = "random"
MODES = {
    MODE_PER_TYPE: "En per variationstyp",
    MODE_ALL: "Alla valda variationer",
    MODE_RANDOM: "Slumpvisa kombinationer",
}


@dataclass
class AnnotatedImage:
    frame: np.ndarray
    annotations: list[dict]


@dataclass(frozen=True)
class VariationSettings:
    """Hur de syntetiska bilderna av varje bildpar ska se ut (TASK-88, TASK-106, TASK-117).

    En typ är aktiverad när dess flagga är satt; vändningen aktiveras av sina
    riktningar. Styrkan är den största förändringen, så rotation 30 ger en
    vinkel i intervallet -30 till 30 grader, och storleken dras mellan
    scale_down_percent under och scale_up_percent över originalet. Läget avgör
    vad en bild får: en typ, alla aktiva typer eller ett slumpvis urval av dem.
    Antalet variationer per bildpar gäller bara när en bild får flera typer; en
    bild per variationstyp ger i stället en bild per aktiv typ.
    """

    count: int = 0
    mode: str = MODE_PER_TYPE
    rotation: bool = False
    rotation_degrees: float = 0.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    scale: bool = False
    scale_up_percent: float = 0.0
    scale_down_percent: float = 0.0
    color: bool = False
    color_percent: float = 0.0

    @property
    def flip_count(self) -> int:
        """Antal valda vändningsriktningar."""
        return int(self.flip_horizontal) + int(self.flip_vertical)

    @property
    def active_types(self) -> list[str]:
        """De aktiverade variationstyperna, i den ordning de appliceras."""
        types = []
        if self.rotation:
            types.append("rotation")
        if self.flip_count:
            types.append("flip")
        if self.scale:
            types.append("scale")
        if self.color:
            types.append("color")
        return types

    @property
    def total(self) -> int:
        """Antal syntetiska bilder som varje bildpar får."""
        types = self.active_types
        if not types:
            return 0
        # en bild per variationstyp ger en bild per aktiv typ, inte count bilder
        return len(types) if self.mode == MODE_PER_TYPE else self.count
