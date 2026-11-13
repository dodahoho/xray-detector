"""Modellens indatastorlek i pixlar (TASK-79, TASK-80).

Ultralytics kräver att bildstorleken är en multipel av 32, och både
träningen och inferensen utgår från källans upplösning. Avrundningen och
gränserna bor här så de två vägarna inte kan glida isär.
"""

STEP = 32
MIN_SIZE = 320
MAX_SIZE = 1920
DEFAULT_SIZE = 640


def round_size(value: int) -> int:
    """Avrundar uppåt till närmaste multipel av 32 inom [320, 1920]."""
    rounded = -(-int(value) // STEP) * STEP
    return max(MIN_SIZE, min(MAX_SIZE, rounded))
