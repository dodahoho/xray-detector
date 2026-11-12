"""Klassfärger ska vara stabila mellan sessioner och vyer (TASK-5, TASK-76)."""

import inspect
import subprocess
import sys

from PySide6.QtGui import QColor

from xray_detector.ui.colors import CLASS_COLORS, class_color


def test_same_class_gets_the_same_color_every_time():
    assert class_color("pistol").rgb() == class_color("pistol").rgb()


def test_color_depends_only_on_the_class_name():
    """Färgen får inte avgöras av en klasslista (TASK-76).

    Tidigare mappades en känd klass till sin plats i listan, så samma klass
    fick olika färg beroende på vilken lista som skickades in och i vilken
    ordning den låg. Signaturkontrollen hindrar att listan smygs tillbaka.
    """
    assert list(inspect.signature(class_color).parameters) == ["class_name"]


def test_unknown_class_survives_hash_seed_change():
    # hashen beror inte av Pythons hash-seed: samma namn ger alltid samma färg
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


def test_palette_colors_are_distinct():
    assert len({color.rgb() for color in CLASS_COLORS}) == len(CLASS_COLORS)
    assert all(isinstance(color, QColor) for color in CLASS_COLORS)


def test_classes_spread_over_the_palette():
    """Många klasser ska sprida sig över paletten, inte fastna på få färger."""
    seen = {class_color(f"klass{index}").rgb() for index in range(64)}
    assert len(seen) == len(CLASS_COLORS)
