"""Resursstaplar i detektionsläget (TASK-31)."""

import pytest
from PySide6.QtCore import QSettings

from xray_detector.domain.config import AppConfig
from xray_detector.infrastructure.system.resources import ResourceMonitor, ResourceUsage
from xray_detector.ui.detection_view import DetectionView, ResourceMeter, _format_bytes


@pytest.fixture
def view(qapp, tmp_path) -> DetectionView:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    return DetectionView(config, settings)


def test_monitor_samples_cpu_and_ram():
    usage = ResourceMonitor().sample()

    assert usage.cpu_percent is not None
    assert usage.cpu_count and usage.cpu_count >= 1
    assert usage.ram_bytes and usage.ram_bytes > 0
    assert usage.ram_total_bytes and usage.ram_total_bytes > usage.ram_bytes


def test_format_bytes_units():
    assert _format_bytes(None) == ""
    assert _format_bytes(512) == "512 B"
    assert _format_bytes(1536) == "1.5 kB"
    assert _format_bytes(2 * 1024**3) == "2.0 GB"


def test_meter_shows_na_without_value(qapp):
    meter = ResourceMeter("GPU")

    meter.set_usage(None, "")

    assert meter.value.text() == "n/a"
    assert meter.bar.value() == 0


def test_meter_sets_bar_and_text(qapp):
    meter = ResourceMeter("CPU")

    meter.set_usage(0.42, "42%")

    assert meter.bar.value() == 42
    assert meter.value.text() == "42%"


def test_detection_view_has_all_meters(view):
    assert set(view.resource_meters) == {"gpu", "vram", "cpu", "ram"}


def test_detection_view_shows_resource_usage(view):
    view._apply_usage(ResourceUsage(
        cpu_percent=42.0,
        cpu_count=1,
        ram_bytes=2 * 1024**3,
        ram_total_bytes=16 * 1024**3,
        gpu_percent=17.0,
        vram_bytes=1024**3,
        vram_total_bytes=8 * 1024**3,
    ))

    assert view.resource_meters["cpu"].bar.value() == 42
    assert view.resource_meters["cpu"].value.text() == "42%"
    assert view.resource_meters["gpu"].bar.value() == 17
    assert view.resource_meters["gpu"].value.text() == "17%"
    assert view.resource_meters["vram"].value.text() == "1.0 GB / 8.0 GB"
    assert view.resource_meters["ram"].value.text() == "2.0 GB"


def test_detection_view_shows_na_without_gpu(view):
    view._apply_usage(ResourceUsage(
        cpu_percent=5.0,
        cpu_count=1,
        ram_bytes=1024**2,
        ram_total_bytes=1024**3,
    ))

    assert view.resource_meters["gpu"].value.text() == "n/a"
    assert view.resource_meters["vram"].value.text() == "n/a"
    assert view.resource_meters["gpu"].bar.value() == 0
    assert view.resource_meters["cpu"].value.text() == "5%"
