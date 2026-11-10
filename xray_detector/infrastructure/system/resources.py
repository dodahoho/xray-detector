"""Applikationens resursanvändning: CPU, RAM, GPU och VRAM (TASK-31)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceUsage:
    """Ett ögonblicksvärde för appens resursanvändning.

    Fälten är None när resursen inte kan mätas, t.ex. GPU utan CUDA.
    """

    cpu_percent: float | None = None
    cpu_count: int | None = None
    ram_bytes: int | None = None
    ram_total_bytes: int | None = None
    gpu_percent: float | None = None
    vram_bytes: int | None = None
    vram_total_bytes: int | None = None


class ResourceMonitor:
    """Samplar den egna processens CPU/RAM och GPU:ns VRAM via torch."""

    def __init__(self) -> None:
        self._process = None
        try:
            import psutil

            self._process = psutil.Process()
            # primer: psutil.cpu_percent() ger alltid 0.0 första gången
            self._process.cpu_percent()
        except Exception:
            self._process = None

    def sample(self) -> ResourceUsage:
        cpu, cpu_count, ram, ram_total = self._cpu_ram()
        gpu, vram, vram_total = self._gpu()
        return ResourceUsage(
            cpu_percent=cpu,
            cpu_count=cpu_count,
            ram_bytes=ram,
            ram_total_bytes=ram_total,
            gpu_percent=gpu,
            vram_bytes=vram,
            vram_total_bytes=vram_total,
        )

    def _cpu_ram(self) -> tuple[float | None, int | None, int | None, int | None]:
        if self._process is None:
            return None, None, None, None
        try:
            import psutil

            return (
                float(self._process.cpu_percent()),
                int(psutil.cpu_count() or 0) or None,
                int(self._process.memory_info().rss),
                int(psutil.virtual_memory().total),
            )
        except Exception:
            return None, None, None, None

    def _gpu(self) -> tuple[float | None, int | None, int | None]:
        try:
            import torch
        except ImportError:
            return None, None, None
        try:
            if not torch.cuda.is_available():
                return None, None, None
        except Exception:
            return None, None, None
        try:
            percent = float(torch.cuda.utilization())
        except Exception:
            percent = None
        try:
            allocated = int(torch.cuda.memory_allocated())
            total = int(torch.cuda.get_device_properties(0).total_memory)
        except Exception:
            allocated, total = None, None
        return percent, allocated, total
