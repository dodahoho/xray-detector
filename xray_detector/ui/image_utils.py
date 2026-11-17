"""Bildkonvertering delad mellan vyerna (TASK-140).

OpenCV arbetar i BGR och Qt ritar RGB. Konverteringen låg tidigare i tre
kopior, med olika hantering av bufferten; här finns en implementation som
alltid lämnar ifrån sig en egen kopia, så bilden inte pekar på en numpy-array
som frigörs när funktionen returnerar.
"""

import cv2
import numpy as np
from PySide6.QtGui import QImage


def bgr_to_qimage(frame: np.ndarray) -> QImage:
    """BGR-ramen som en RGB-QImage som äger sina pixlar."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    return QImage(
        rgb.data, width, height, channels * width, QImage.Format.Format_RGB888
    ).copy()
