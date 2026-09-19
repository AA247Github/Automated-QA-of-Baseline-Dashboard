"""Shared record layouts passed between the loading, checking and output stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class InputPaths:
    # The four submitted files plus any selected service profile.
    folder: Path
    csv: Optional[Path] = None
    sql: Optional[Path] = None
    pdf: Optional[Path] = None
    mapping: Optional[Path] = None
    profile: Optional[Path] = None


@dataclass
class MetricSpec:
    """One count or total taken from the SQL."""

    metric_id: str
    name: str
    chart: str
    expression: str
    kind: str = "count"  # count | sum
    sql_alias: str = ""
    query_label: str = ""
    where_extra: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    source_sql: str = ""

    def combined_expression(self) -> str:
        # Joins the calculation rule to any patient-level SQL filter.
        parts = [self.expression.strip()] if self.expression.strip() else []
        extra = (self.where_extra or "").strip()
        if extra:
            parts.append(f"({extra})")
        if not parts:
            return "TRUE"
        if len(parts) == 1:
            return parts[0]
        return " and ".join(f"({p})" for p in parts)


@dataclass
class HelperCheckSpec:
    # Describes a relationship expected between two helper calculations.
    check_id: str
    name: str
    left: str
    right: str
    description: str = ""
    kind: str = "equivalent"  # equivalent | implies


@dataclass
class MetricResult:
    # Stores the source calculation, dashboard comparison and supporting rows.
    spec: MetricSpec
    csv_value: Optional[float]
    dashboard_value: Optional[float]
    status: str
    error: str = ""
    patient_ids: list[str] = field(default_factory=list)
    used_columns: list[str] = field(default_factory=list)
    pdf_evidence: str = ""
    sheet_name: str = ""
    csv_filename: str = ""

    @property
    def csv_count(self) -> int:
        if self.csv_value is None:
            return 0
        return int(self.csv_value)


@dataclass
class HelperResult:
    # Stores the outcome and exceptions from a helper-column check.
    spec: HelperCheckSpec
    mismatches: int
    left_only: int
    right_only: int
    both: int
    neither: int
    mismatch_ids: list[str] = field(default_factory=list)
    status: str = "PASS"
    error: str = ""


@dataclass
class FileFingerprint:
    # Identifies the exact file version included in the evidence.
    path: str
    sha256: str
    bytes: int


@dataclass
class RunResult:
    # Collects everything needed by the screen, workbook and written report.
    inputs: InputPaths
    fingerprints: list[FileFingerprint]
    metrics: list[MetricResult]
    helpers: list[HelperResult]
    mapping: dict[str, str]
    unmapped_sql: list[str]
    pdf_text: str
    notes: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)
