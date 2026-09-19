"""Writes the human-readable and machine-readable QA summaries."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from accuracy_check.models import RunResult


def write_markdown_report(result: RunResult, path: Path) -> None:
    # Counts the outcome groups used in the report overview.
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    match_n = sum(1 for m in result.metrics if m.status == "MATCH")
    mismatch_n = sum(1 for m in result.metrics if m.status == "MISMATCH")
    csv_only_n = sum(1 for m in result.metrics if m.status == "CSV_ONLY")
    error_n = sum(1 for m in result.metrics if m.status == "ERROR")
    helper_fail = [h for h in result.helpers if h.status != "PASS"]

    # Starts with the run context and exact source-file fingerprints.
    lines = [
        "# Dashboard accuracy-check report",
        "",
        f"Generated: {now}",
        "",
    ]
    service = result.extras.get("service_name")
    therapy = result.extras.get("therapy_area")
    dash_type = result.extras.get("dashboard_type")
    if service or therapy or dash_type:
        bits = [x for x in (service, therapy, dash_type) if x]
        lines += [f"Service: **{' · '.join(bits)}**", ""]
    # Adds the QA outcome, process checklist and every extracted metric.
    lines += [
        "This report is the written proof that each SQL count/sum was rebuilt from the CLIICS CSV using the same filters, then compared to the dashboard printout.",
        "",
        "## Inputs",
        "",
        f"- Folder: `{result.inputs.folder}`",
        f"- CSV: `{result.inputs.csv.name if result.inputs.csv else 'missing'}`",
        f"- SQL: `{result.inputs.sql.name if result.inputs.sql else 'missing'}`",
        f"- Dashboard PDF: `{result.inputs.pdf.name if result.inputs.pdf else 'missing'}`",
        f"- Mapping: `{result.inputs.mapping.name if result.inputs.mapping else 'missing'}`",
        "",
        "## File fingerprints",
        "",
        "| File | Bytes | SHA256 |",
        "|---|---:|---|",
    ]
    for fp in result.fingerprints:
        lines.append(f"| `{Path(fp.path).name}` | {fp.bytes} | `{fp.sha256}` |")

    lines += [
        "",
        "## Outcome",
        "",
        f"- Metrics extracted from SQL: **{len(result.metrics)}**",
        f"- Match dashboard: **{match_n}**",
        f"- Mismatch: **{mismatch_n}**",
        f"- CSV replicated, PDF not uniquely labelled: **{csv_only_n}**",
        f"- Errors: **{error_n}**",
        f"- Helper checks failed: **{len(helper_fail)}**",
        "",
        "## Process checklist",
        "",
        "| Step | Status |",
        "|---|---|",
        f"| 1. Review dashboard PDF | {'Done' if result.pdf_text else 'Missing'} |",
        f"| 2. Review CLIICS CSV export | {'Done' if result.inputs.csv else 'Missing'} |",
        f"| 3. Read BI SQL | {'Done' if result.inputs.sql else 'Missing'} |",
        f"| 4. Apply column mapping | {len(result.mapping)} fields |",
        f"| 5. Replicate each SQL sum on the CSV | {len(result.metrics) - error_n} / {len(result.metrics)} |",
        f"| 6. Compare to dashboard printout | {match_n} match / {mismatch_n} mismatch / {csv_only_n} review |",
        f"| 7. Helper / clinical sense checks | {len(result.helpers) - len(helper_fail)} / {len(result.helpers)} passed |",
        "| 8. Evidence sheets (one per sum) | See QA_Evidence.xlsx and evidence_csvs/ |",
        "| 9. Sign-off | Complete 03_Signoff in the evidence workbook |",
        "",
        "## Metric results",
        "",
        "| Status | Chart | Metric | CSV | Dashboard | SQL |",
        "|---|---|---|---:|---:|---|",
    ]
    for item in result.metrics:
        sql = item.spec.combined_expression().replace("|", "\\|")
        dash = item.dashboard_value if item.dashboard_value is not None else ""
        csv_v = item.csv_value if item.csv_value is not None else ""
        lines.append(
            f"| {item.status} | {item.spec.chart} | {item.spec.name} | {csv_v} | {dash} | `{sql}` |"
        )

    # Service-specific helper checks are included only when a profile supplied them.
    if result.helpers:
        lines += ["", "## Helper column checks", ""]
        lines.append("| Status | Check | Mismatches | Left only | Right only |")
        lines.append("|---|---|---:|---:|---:|")
        for item in result.helpers:
            lines.append(
                f"| {item.status} | {item.spec.name} | {item.mismatches} | {item.left_only} | {item.right_only} |"
            )
            if item.mismatch_ids:
                lines.append(f"|  | Example IDs: {', '.join(item.mismatch_ids[:12])} | | | |")

    if result.notes:
        lines += ["", "## Notes", ""]
        lines.extend(f"- {note}" for note in result.notes)

    lines += [
        "",
        "## How to verify a number by hand",
        "",
        "1. Open `QA_Evidence.xlsx`.",
        "2. Use the Summary sheet to find the metric.",
        "3. Open that metric's sheet (or the matching file in `evidence_csvs/`).",
        "4. Count the patient rows — or use the `ROW_COUNT` footer.",
        "5. That count is the internal calculation of the SQL expression against this CSV.",
        "",
        "CSV-only rows still have a proven CSV count. Confirm the printed dashboard bar/label by eye when the PDF extractor cannot uniquely bind a number.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json_result(result: RunResult, path: Path) -> None:
    # Stores the same result in a stable format for later automation.
    payload = {
        "folder": str(result.inputs.folder),
        "inputs": {
            "csv": str(result.inputs.csv) if result.inputs.csv else None,
            "sql": str(result.inputs.sql) if result.inputs.sql else None,
            "pdf": str(result.inputs.pdf) if result.inputs.pdf else None,
            "mapping": str(result.inputs.mapping) if result.inputs.mapping else None,
        },
        "fingerprints": [fp.__dict__ for fp in result.fingerprints],
        "metrics": [
            {
                "id": m.spec.metric_id,
                "chart": m.spec.chart,
                "name": m.spec.name,
                "expression": m.spec.combined_expression(),
                "kind": m.spec.kind,
                "csv_value": m.csv_value,
                "dashboard_value": m.dashboard_value,
                "status": m.status,
                "sheet": m.sheet_name,
                "csv_file": m.csv_filename,
                "pdf_evidence": m.pdf_evidence,
                "error": m.error,
                "n_patients": len(m.patient_ids),
            }
            for m in result.metrics
        ],
        "helpers": [
            {
                "id": h.spec.check_id,
                "name": h.spec.name,
                "status": h.status,
                "mismatches": h.mismatches,
                "left_only": h.left_only,
                "right_only": h.right_only,
                "error": h.error,
            }
            for h in result.helpers
        ],
        "notes": result.notes,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
