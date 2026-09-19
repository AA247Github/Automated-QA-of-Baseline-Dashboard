"""Loads optional service rules while keeping a generic default."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AppConfig:
    # These settings control evidence detail, known labels and service-specific checks.
    name: str = "Dashboard accuracy check"
    evidence_mode: str = "key_columns"  # key_columns | full
    always_include_columns: list[str] = field(default_factory=lambda: ["ID", "Age in years", "Gender"])
    helper_checks: list[dict[str, str]] = field(default_factory=list)
    dashboard_labels: dict[str, list[str]] = field(default_factory=dict)
    value_maps: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    extra_metrics: list[dict[str, Any]] = field(default_factory=list)
    ignore_zero_chart_rows: bool = False
    notes: list[str] = field(default_factory=list)
    match_keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        # Reads only recognised settings so stray profile fields cannot alter a run.
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)


def default_profile_dir() -> Path:
    # Service profiles are kept beside the application code.
    return Path(__file__).resolve().parent / "profiles"


def load_config(path: Path | None) -> AppConfig:
    # No selected profile means the framework runs with generic rules.
    if path is None:
        return AppConfig()
    return AppConfig.from_yaml(path)
