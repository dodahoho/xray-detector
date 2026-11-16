"""Syntetiska variationer av datasetets bilder (TASK-88).

En variation räknas först fram som en beskrivning i en plan och appliceras
sedan på varje bild i bildparet, så vänster- och högerbilden får samma
rotation, vändning, storlek och färg. Annoteringarna flyttas med samma
matris som bilden, så rutorna ligger kvar på objekten.

Rotation och storlek ändrar bildens mått i stället för att klippa bort
innehåll: en roterad bild får plats med hela den roterade rektangeln, och en
skalad bild blir större eller mindre. Då behåller varje objekt sin annotering,
vilket är hela poängen med att utöka ett litet dataset. Ytan utanför en
roterad bild blir svart, vilket röntgenbilder redan har som bakgrund.
"""

import random

import cv2
import numpy as np

from xray_detector.domain.dataset import VariationSettings

# skalningen kläms hit, så en stor variation inte krymper bilden till ingenting
MIN_SCALE = 0.25
MAX_SCALE = 4.0
# ljusstyrkan räknas som andel av det största värdet en kanal kan ha
BRIGHTNESS_RANGE = 127.0


def variation_plan(
    settings: VariationSettings,
    rng: random.Random,
) -> list[dict]:
    """Parametrarna för en uppsättning variationer, en beskrivning per variation.

    Planen räknas fram en gång per bildpar, så båda bilderna i paret får
    samma variation. Beskrivningen sparas i datasetets metadata och används
    som tooltip i datasetvyn.
    """
    plan: list[dict] = []
    for _ in range(settings.rotation_count):
        angle = rng.uniform(-settings.rotation_degrees, settings.rotation_degrees)
        plan.append({"type": "rotation", "angle": round(angle, 1)})
    if settings.flip_horizontal:
        plan.append({"type": "flip", "axis": "horizontal"})
    if settings.flip_vertical:
        plan.append({"type": "flip", "axis": "vertical"})
    for _ in range(settings.scale_count):
        factor = 1 + rng.uniform(-settings.scale_percent, settings.scale_percent) / 100
        plan.append(
            {"type": "scale", "factor": round(min(MAX_SCALE, max(MIN_SCALE, factor)), 2)}
        )
    for _ in range(settings.color_count):
        percent = settings.color_percent / 100
        plan.append(
            {
                "type": "color",
                "contrast": round(rng.uniform(1 - percent, 1 + percent), 2),
                "brightness": round(rng.uniform(-percent, percent) * BRIGHTNESS_RANGE),
            }
        )
    return plan


def apply_variation(
    frame: np.ndarray,
    annotations: list[dict],
    variation: dict,
) -> tuple[np.ndarray, list[dict]]:
    """Bilden och annoteringarna efter variationen.

    En okänd typ lämnar bilden orörd, så en post i metadata som appen inte
    känner igen inte kraschar en utökning.
    """
    kind = variation.get("type")
    if kind == "rotation":
        return rotate(frame, annotations, float(variation["angle"]))
    if kind == "flip":
        return flip(frame, annotations, variation["axis"] == "horizontal")
    if kind == "scale":
        return scale(frame, annotations, float(variation["factor"]))
    if kind == "color":
        return adjust_color(
            frame,
            annotations,
            float(variation["contrast"]),
            float(variation["brightness"]),
        )
    return frame, [dict(annotation) for annotation in annotations]


def describe(variation: dict) -> str:
    """Variationen som text, till tooltip och statusrad."""
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


def rotate(
    frame: np.ndarray,
    annotations: list[dict],
    angle: float,
) -> tuple[np.ndarray, list[dict]]:
    """Roterar bilden kring mitten och vidgar den så inget klipps bort."""
    height, width = frame.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    corners = np.array(
        [[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float64
    )
    points = corners @ matrix[:, :2].T + matrix[:, 2]
    left, top = points.min(axis=0)
    right, bottom = points.max(axis=0)
    # flytta den roterade bilden till rätt plats i den nya, större ramen
    matrix[0, 2] -= left
    matrix[1, 2] -= top
    size = (max(1, round(right - left)), max(1, round(bottom - top)))
    warped = cv2.warpAffine(
        frame,
        matrix,
        size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return warped, _transform(annotations, matrix, size[0], size[1])


def scale(
    frame: np.ndarray,
    annotations: list[dict],
    factor: float,
) -> tuple[np.ndarray, list[dict]]:
    """Skalar bilden och annoteringarna med samma faktor."""
    height, width = frame.shape[:2]
    size = (max(1, round(width * factor)), max(1, round(height * factor)))
    interpolation = cv2.INTER_AREA if factor < 1 else cv2.INTER_LINEAR
    scaled = cv2.resize(frame, size, interpolation=interpolation)
    # måtten avrundas till hela pixlar, så rutorna följer bildens nya mått
    scale_x = size[0] / width
    scale_y = size[1] / height
    moved = [
        {
            **annotation,
            "bbox": [
                annotation["bbox"][0] * scale_x,
                annotation["bbox"][1] * scale_y,
                annotation["bbox"][2] * scale_x,
                annotation["bbox"][3] * scale_y,
            ],
        }
        for annotation in annotations
    ]
    return scaled, moved


def flip(
    frame: np.ndarray,
    annotations: list[dict],
    horizontal: bool,
) -> tuple[np.ndarray, list[dict]]:
    """Speglar bilden och flyttar annoteringarna till spegelbilden."""
    height, width = frame.shape[:2]
    flipped = cv2.flip(frame, 1 if horizontal else 0)
    moved = []
    for annotation in annotations:
        x, y, w, h = annotation["bbox"]
        if horizontal:
            x = width - (x + w)
        else:
            y = height - (y + h)
        moved.append({**annotation, "bbox": [x, y, w, h]})
    return flipped, moved


def adjust_color(
    frame: np.ndarray,
    annotations: list[dict],
    contrast: float,
    brightness: float,
) -> tuple[np.ndarray, list[dict]]:
    """Ändrar kontrast och ljusstyrka; annoteringarna ligger kvar."""
    adjusted = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness)
    return adjusted, [dict(annotation) for annotation in annotations]


def _transform(
    annotations: list[dict],
    matrix: np.ndarray,
    width: int,
    height: int,
) -> list[dict]:
    """Flyttar annoteringarna med matrisen och klipper dem mot bilden.

    Den roterade rutan blir den minsta axelräta ruta som rymmer hörnen. En
    ruta som hamnar utanför bilden kortas av, och en ruta som blir mindre än
    en pixel tas bort, eftersom den inte längre är ett objekt.
    """
    moved = []
    for annotation in annotations:
        x, y, w, h = annotation["bbox"]
        corners = np.array(
            [[x, y], [x + w, y], [x, y + h], [x + w, y + h]], dtype=np.float64
        )
        points = corners @ matrix[:, :2].T + matrix[:, 2]
        left, top = points.min(axis=0)
        right, bottom = points.max(axis=0)
        bbox = _clip(left, top, right - left, bottom - top, width, height)
        if bbox is not None:
            moved.append({**annotation, "bbox": bbox})
    return moved


def _clip(
    x: float,
    y: float,
    w: float,
    h: float,
    width: int,
    height: int,
) -> list[float] | None:
    """Rutan klippt mot bilden; None när inget av objektet är kvar."""
    left = max(0.0, min(float(width), x))
    top = max(0.0, min(float(height), y))
    right = max(0.0, min(float(width), x + w))
    bottom = max(0.0, min(float(height), y + h))
    if right - left < 1 or bottom - top < 1:
        return None
    return [left, top, right - left, bottom - top]
