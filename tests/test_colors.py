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


def test_device_color_is_green_only_for_cuda():
    """Enhetsradens färg kommer ur etiketten, inte ur en hårdkodad sträng (TASK-139)."""
    from xray_detector.ui.colors import DEVICE_CPU_COLOR, DEVICE_CUDA_COLOR, device_color

    assert device_color("Enhet: CUDA (RTX 5090)") == DEVICE_CUDA_COLOR
    assert device_color("Enhet: CPU (CUDA ej tillgänglig)") == DEVICE_CPU_COLOR
    assert device_color("Enhet: PyTorch saknas") == DEVICE_CPU_COLOR


def test_device_status_builds_on_the_single_cuda_label(monkeypatch):
    """device_status delegerar till cuda_device_label (TASK-139)."""
    from xray_detector.application import model_registry

    monkeypatch.setattr(
        model_registry, "cuda_device_label", lambda: "CUDA (testkort)"
    )

    assert model_registry.device_status() == "Enhet: CUDA (testkort)"


def test_no_css_colors_are_hardcoded_outside_colors_py():
    """Nya ytor ska hämta sin färg ur ui/colors.py (TASK-139)."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "xray_detector"
    pattern = re.compile(r"#[0-9a-fA-F]{3,6}\b")
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "colors.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(root)}:{number}")

    assert offenders == [], f"hårdkodade färger utanför ui/colors.py: {offenders}"


def test_the_detection_display_follows_the_theme(qapp):
    """Videoytans bakgrund kommer ur paletten, inte ur en mörk konstant (TASK-144)."""
    from xray_detector.ui.stream_panel import StreamPanel

    panel = StreamPanel("left")

    assert panel.display.autoFillBackground(), "ytan fyller inte med palettfärgen"
    assert "background" not in panel.display.styleSheet()
