"""Shared helpers for the CLI and HTML front end."""

from __future__ import annotations

from pathlib import Path

from accuracy_check.config import default_profile_dir, load_config
from accuracy_check.models import RunResult


def list_profiles() -> list[dict]:
    # Builds the dropdown from generic choices and available service profiles.
    items = [
        {
            "id": "auto",
            "name": "Auto-detect from service name, therapy area and file names",
            "keywords": [],
        },
        {
            "id": "generic",
            "name": "Generic - SQL, mapping and PDF only (any service)",
            "keywords": [],
        },
    ]
    for path in sorted(default_profile_dir().glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        cfg = load_config(path)
        items.append(
            {
                "id": path.stem,
                "name": cfg.name,
                "keywords": list(cfg.match_keywords),
            }
        )
    return items


def resolve_profile(choice: str | None, hints: str = "") -> Path | None:
    # Uses the chosen profile or finds the best keyword match for Auto-detect.
    choice = (choice or "auto").strip().lower()
    if choice in {"", "generic", "none"}:
        return None
    if choice != "auto":
        path = Path(choice)
        if path.is_file():
            return path
        candidate = default_profile_dir() / f"{choice}.yaml"
        return candidate if candidate.is_file() else None

    blob = hints.lower()
    best: Path | None = None
    best_score = 0
    for path in default_profile_dir().glob("*.yaml"):
        if path.name.startswith("_"):
            continue
        cfg = load_config(path)
        score = sum(1 for key in cfg.match_keywords if key.lower() in blob)
        if score > best_score:
            best_score = score
            best = path
    return best if best_score else None


def summarise_run(result: RunResult) -> dict:
    # Reduces the full result to the figures and rows displayed by the web page.
    match_n = sum(1 for m in result.metrics if m.status == "MATCH")
    mismatch_n = sum(1 for m in result.metrics if m.status == "MISMATCH")
    csv_only_n = sum(1 for m in result.metrics if m.status == "CSV_ONLY")
    error_n = sum(1 for m in result.metrics if m.status == "ERROR")
    helper_pass = sum(1 for h in result.helpers if h.status == "PASS")
    return {
        "service_name": result.extras.get("service_name", ""),
        "therapy_area": result.extras.get("therapy_area", ""),
        "dashboard_type": result.extras.get("dashboard_type", ""),
        "profile_name": result.extras.get("profile_name", ""),
        "metrics": len(result.metrics),
        "match": match_n,
        "mismatch": mismatch_n,
        "csv_only": csv_only_n,
        "errors": error_n,
        "helpers_passed": helper_pass,
        "helpers_total": len(result.helpers),
        "mapping_fields": len(result.mapping),
        "csv_rows": (result.extras.get("csv_info") or {}).get("n_rows"),
        "notes": result.notes,
        "rows": [
            {
                "status": item.status,
                "chart": item.spec.chart,
                "name": item.spec.name,
                "csv_value": item.csv_value,
                "dashboard_value": item.dashboard_value,
                "expression": item.spec.combined_expression(),
                "sheet": item.sheet_name,
                "error": item.error,
            }
            for item in result.metrics
        ],
        "helpers": [
            {
                "name": item.spec.name,
                "status": item.status,
                "mismatches": item.mismatches,
                "error": item.error,
            }
            for item in result.helpers
        ],
    }
