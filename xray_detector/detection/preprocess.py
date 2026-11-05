"""Preprocessing av röntgenbilder.

Röntgenbilder är ofta inverterade (mörk bakgrund, ljusa objekt) och kan ha
låg kontrast. Denna modul erbjuder konfigurerbara transformationer.
"""
from __future__ import annotations

import cv2
import numpy as np


def _apply_clahe(frame: np.ndarray) -> np.ndarray:
    """Kontrastförbättring som bevarar färg om bilden är i färg.

    CLAHE appliceras på ljuskanalen (L i LAB) så att färgströmmar inte blir
    gråskala. Gråskalebilder behandlas direkt.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    if frame.ndim == 2:
        return clahe.apply(frame)

    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    l_chan = clahe.apply(l_chan)
    return cv2.cvtColor(cv2.merge((l_chan, a_chan, b_chan)), cv2.COLOR_LAB2BGR)


def preprocess(frame: np.ndarray, mode: str) -> np.ndarray:
    """Applikerar preprocessing enligt mode.

    mode:
      - "none":   oförändrad
      - "invert": invertera (mörk bakgrund → ljus)
      - "clahe":  kontrastförbättring (CLAHE), bevarar färg
      - "auto":   CLAHE (bevarar färg; gråskala förblir gråskala)
    """
    if frame is None:
        return frame
    if mode in ("none", None):
        return frame

    if mode in ("clahe", "auto"):
        frame = _apply_clahe(frame)

    if mode == "invert":
        frame = cv2.bitwise_not(frame)

    return frame
