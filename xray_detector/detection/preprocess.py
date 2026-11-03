"""Preprocessing av röntgenbilder.

Röntgenbilder är ofta inverterade (mörk bakgrund, ljusa objekt) och kan ha
låg kontrast. Denna modul erbjuder konfigurerbara transformationer.
"""
from __future__ import annotations

import cv2
import numpy as np


def preprocess(frame: np.ndarray, mode: str) -> np.ndarray:
    """Applikerar preprocessing enligt mode.

    mode:
      - "none":   oförändrad
      - "invert": invertera (mörk bakgrund → ljus)
      - "clahe":  kontrastförbättring (CLAHE) på gråskala
      - "auto":   gråskala + CLAHE (rimligt default för röntgen)
    """
    if frame is None:
        return frame
    if mode in ("none", None):
        return frame

    # Säkerställ gråskala för CLAHE
    if mode in ("clahe", "auto"):
        if frame.ndim == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        frame = clahe.apply(gray)

    if mode == "invert":
        frame = cv2.bitwise_not(frame)

    return frame
