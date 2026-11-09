"""Klassfärger ska vara stabila mellan sessioner och vyer (TASK-5)."""

from PySide6.QtGui import QColor

from xray_detector.ui.colors import CLASS_COLORS, class_color

KNOWN = ["cigaretter", "cannabis", "kniv", "pistol"]


def test_known_classes_map_by_list_index():
    colors = [class_color(name, KNOWN) for name in KNOWN]
    assert colors == CLASS_COLORS[:4]
    assert len({color.rgb() for color in colors}) == 4


def test_unknown_class_is_deterministic():
    a = class_color("ny_klass")
    b = class_color("ny_klass")
    assert a.rgb() == b.rgb()


def test_unknown_class_survives_hash_seed_change():
    # crc32 beror inte av Pythons hash-seed: samma namn ger alltid samma färg
    import subprocess
    import sys

    code = (
        "from xray_detector.ui.colors import class_color;"
        "print(class_color('sprayburk').rgb())"
    )
    results = {
        subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                        env={"PYTHONHASHSEED": str(seed), "PATH": ""}, check=False).stdout.strip()
        for seed in (0, 1, 12345)
    }
    assert len(results) == 1, results


def test_colors_distinct_for_many_classes():
    seen = {class_color(f"klass{i}").rgb() for i in range(16)}
    assert len(seen) == len(CLASS_COLORS)
    assert all(isinstance(color, QColor) for color in CLASS_COLORS)
