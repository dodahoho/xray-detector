"""Atomisk JSON-skrivning (TASK-3).

En krasch mitt i en direkt skrivning korrumperar hela filen (t.ex.
dataset.json for en version). atomic_write_json skriver därför till en
temporär fil i samma katalog, synkar till disk och byter ut målet med
os.replace(), som är atomärt på samma volume: antingen den gamla eller
den nya kompletta filen finns kvar.
"""

import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path: Path, payload, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=indent)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
