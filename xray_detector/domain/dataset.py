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


#: Skalningen kläms hit, så en stor variation inte krymper bilden till ingenting.
MIN_SCALE = 0.25
MAX_SCALE = 4.0


def describe(variation) -> str:
    """Variationen som text, till tooltip och statusrad.

    En syntetisk bild kan bära flera variationer (TASK-106), och äldre dataset
    sparade en enstaka, så båda formerna läses. Ligger i domain så lagringen
    och vyerna läser samma beskrivning (TASK-143).
    """
    if isinstance(variation, list):
        return ", ".join(describe(item) for item in variation) or "variation"
    kind = variation.get("type")
    if kind == "rotation":
        return f"rotation {variation['angle']:g}°"
    if kind == "flip":
        return "vänd " + (
            "horisontellt" if variation["axis"] == "horizontal" else "vertikalt"
        )
    if kind == "scale":
        return f"storlek {variation['factor']:g}×"
    if kind == "color":
        return (
            f"färg kontrast {variation['contrast']:g}×, "
            f"ljusstyrka {variation['brightness']:+g}"
        )
    return "variation"


def capture_group(image: dict) -> object:
    """Fångstgruppen en bild hör till: grupp-id, annars bildens eget id (TASK-137)."""
    return image.get("group") or image["id"]


def root_image(image: dict, by_id: dict[int, dict]) -> dict:
    """Ursprungsbilden för en syntetisk bild; bilden själv när den är ett original.

    ``source`` pekar på bilden variationen skapades från, och en variation görs
    alltid på ett original. Kedjan följs därför bara så länge källan finns med,
    så en bild vars ursprung saknas i listan behåller sin egen grupp (TASK-111).
    """
    seen: set[int] = set()
    current = image
    while current.get("synthetic"):
        source = by_id.get(current.get("source"))
        if source is None or current["id"] in seen:
            break
        seen.add(current["id"])
        current = source
    return current


def group_images(images: list[dict]) -> dict[object, list[dict]]:
    """Bilderna grupperade per fångstgrupp (bildpar).

    En syntetisk bild hamnar i sin ursprungsbilds grupp, så en utökning av ett
    bildpar aldrig kan läcka mellan train och val (TASK-111). Grupperingen
    definieras här och används av lagringen, exporten, utvärderingen och
    datasetvyn, så de räknar bildpar på samma sätt (TASK-137).
    """
    by_id = {image["id"]: image for image in images}
    groups: dict[object, list[dict]] = {}
    for image in images:
        groups.setdefault(capture_group(root_image(image, by_id)), []).append(image)
    return groups


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
