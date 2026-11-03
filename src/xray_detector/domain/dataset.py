"""Dataset metadata value objects."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DatasetVersionSummary:
    version: str
    created_at: str
    image_count: int
    pair_count: int
    annotation_count: int
    category_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class DatasetInfo:
    name: str
    path: str
    created_at: str
    latest_version: str | None
    next_version: int
