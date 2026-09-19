"""Writes the Excel workbook and filtered CSV files used as QA evidence."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

from accuracy_check.config import AppConfig
from accuracy_check.models import RunResult

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True)
PASS_FILL = PatternFill("solid", fgColor="C6EFCE")
FAIL_FILL = PatternFill("solid", fgColor="FFC7CE")
WARN_FILL = PatternFill("solid", fgColor="FFEB9C")
META_FILL = PatternFill("solid", fgColor="D6DCE4")


def _slug_sheet(index: int, name: str) -> str:
    # Produces a valid, numbered Excel worksheet name.
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    prefix = f"{index:02d}_"
    return (prefix + cleaned)[:31]


def _autosize(ws, max_width: int = 48) -> None:
    # Makes generated sheets readable without excessively wide columns.
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        width = 10
        for cell in col[:40]:
            width = max(width, min(max_width, len(str(cell.value or "")) + 2))
        ws.column_dimensions[letter].width = width


def _style_header(ws, row: int = 1) -> None:
    for cell in ws[row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True)


def write_evidence(
    result: RunResult,
    df: pd.DataFrame,
    id_column: str,
    config: AppConfig,
    output_xlsx: Path,
    csv_dir: Path,
) -> None:
    # Builds the standard workbook sections, then one proof sheet per metric.
    csv_dir.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "00_Summary"
    _write_summary(ws, result)
    _write_mapping(wb, result)
    _write_helpers(wb, result)
    _write_signoff(wb, result)
    _write_metric_sheets(wb, result, df, id_column, config, csv_dir)
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_xlsx)


def _write_summary(ws, result: RunResult) -> None:
    # Gives reviewers one row per result with links to its evidence name.
    ws.append(
        [
            "Metric ID",
            "Chart",
            "Metric",
            "SQL expression",
            "Kind",
            "CSV value",
            "Dashboard value",
            "Status",
            "Evidence sheet",
            "CSV extract",
            "PDF evidence",
            "Error",
        ]
    )
    _style_header(ws)
    for item in result.metrics:
        ws.append(
            [
                item.spec.metric_id,
                item.spec.chart,
                item.spec.name,
                item.spec.combined_expression(),
                item.spec.kind,
                item.csv_value,
                item.dashboard_value,
                item.status,
                item.sheet_name,
                item.csv_filename,
                item.pdf_evidence,
                item.error,
            ]
        )
        fill = {
            "MATCH": PASS_FILL,
            "PASS": PASS_FILL,
            "MISMATCH": FAIL_FILL,
            "FAIL": FAIL_FILL,
            "ERROR": FAIL_FILL,
            "CSV_ONLY": WARN_FILL,
        }.get(item.status)
        if fill:
            ws.cell(ws.max_row, 8).fill = fill
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"
    _autosize(ws, 60)


def _write_mapping(wb, result: RunResult) -> None:
    # Records which CSV heading was used for every mapped SQL field.
    ws = wb.create_sheet("01_Mapping")
    ws.append(["SQL column", "CSV / capture-sheet column"])
    _style_header(ws)
    for sql, csv_name in sorted(result.mapping.items()):
        ws.append([sql, csv_name])
    if result.unmapped_sql:
        ws.append([])
        ws.append(["Unmapped SQL columns referenced by queries"])
        for name in result.unmapped_sql:
            ws.append([name, ""])
    ws.freeze_panes = "A2"
    _autosize(ws)


def _write_helpers(wb, result: RunResult) -> None:
    # Lists helper-column checks and any patient IDs needing review.
    ws = wb.create_sheet("02_Helpers")
    ws.append(
        [
            "Check",
            "Left expression",
            "Right expression",
            "Both",
            "Left only",
            "Right only",
            "Neither",
            "Mismatches",
            "Status",
            "Example IDs",
            "Error",
        ]
    )
    _style_header(ws)
    for item in result.helpers:
        ws.append(
            [
                item.spec.name,
                item.spec.left,
                item.spec.right,
                item.both,
                item.left_only,
                item.right_only,
                item.neither,
                item.mismatches,
                item.status,
                ", ".join(item.mismatch_ids[:15]),
                item.error,
            ]
        )
        ws.cell(ws.max_row, 9).fill = PASS_FILL if item.status == "PASS" else FAIL_FILL
    ws.freeze_panes = "A2"
    _autosize(ws, 50)


def _write_signoff(wb, result: RunResult) -> None:
    # Adds the completion checklist, file fingerprints and manual approval fields.
    ws = wb.create_sheet("03_Signoff")
    ws.append(["Step", "Status", "Notes"])
    _style_header(ws)
    pdf_ok = any(m.status == "MATCH" for m in result.metrics)
    csv_ok = all(m.status != "ERROR" for m in result.metrics)
    helpers_ok = all(h.status == "PASS" for h in result.helpers) if result.helpers else True
    match_n = sum(1 for m in result.metrics if m.status == "MATCH")
    mismatch_n = sum(1 for m in result.metrics if m.status == "MISMATCH")
    csv_only_n = sum(1 for m in result.metrics if m.status == "CSV_ONLY")
    rows = [
        ("Open final dashboard (PDF printout)", "Done" if result.pdf_text else "Missing", result.inputs.pdf.name if result.inputs.pdf else ""),
        ("Open / use CLIICS CSV export", "Done" if result.inputs.csv else "Missing", result.inputs.csv.name if result.inputs.csv else ""),
        ("Obtain SQL file from BI", "Done" if result.inputs.sql else "Missing", result.inputs.sql.name if result.inputs.sql else ""),
        ("Obtain column mapping file", "Done" if result.inputs.mapping else "Missing", result.inputs.mapping.name if result.inputs.mapping else ""),
        ("Read SQL logic for each chart", "Done", f"{len(result.metrics)} countable expressions extracted"),
        ("Match SQL fields to CSV columns", "Done" if result.mapping else "Missing", f"{len(result.mapping)} mapped; {len(result.unmapped_sql)} unmapped"),
        ("Replicate counts from CSV", "Done" if csv_ok else "Errors", f"{len(result.metrics)} metrics"),
        ("Confirm counts match dashboard", "Review", f"{match_n} match, {mismatch_n} mismatch, {csv_only_n} CSV-only"),
        ("Helper / clinical sense checks", "Pass" if helpers_ok else "Fail", f"{len(result.helpers)} checks"),
        ("Evidence workbook produced", "Done", "One sheet per SQL sum plus CSV extracts"),
    ]
    for row in rows:
        ws.append(list(row))
    ws.append([])
    ws.append(["Input fingerprints (proof of what was checked)"])
    ws.append(["File", "SHA256", "Bytes"])
    _style_header(ws, ws.max_row)
    for fp in result.fingerprints:
        ws.append([fp.path, fp.sha256, fp.bytes])
    ws.append([])
    ws.append(["Checker name", ""])
    ws.append(["Date", ""])
    ws.append(["Go-live decision", "Pass / Fail / Pass with comments"])
    ws.append(["Comments", ""])
    _autosize(ws, 70)


def _metric_frame(
    df: pd.DataFrame,
    ids: list[str],
    id_column: str,
    used_columns: list[str],
    config: AppConfig,
) -> pd.DataFrame:
    # Selects the contributing patients and the columns needed to review the rule.
    if config.evidence_mode == "full":
        cols = list(df.columns)
    else:
        extras = []
        for name in config.always_include_columns + used_columns:
            if name in df.columns:
                extras.append(name)
            else:
                # try case-insensitive
                for col in df.columns:
                    if str(col).strip().lower() == name.strip().lower():
                        extras.append(col)
        cols = []
        for col in extras:
            if col not in cols:
                cols.append(col)
        if id_column not in cols and id_column in df.columns:
            cols.insert(0, id_column)
    if not cols:
        cols = [id_column] if id_column in df.columns else list(df.columns[:8])
    if ids and id_column in df.columns:
        mask = df[id_column].astype(str).isin(ids)
        out = df.loc[mask, cols].copy()
    else:
        out = df.loc[[], cols].copy()
    return out


def _write_metric_sheets(
    wb,
    result: RunResult,
    df: pd.DataFrame,
    id_column: str,
    config: AppConfig,
    csv_dir: Path,
) -> None:
    # Writes the same filtered rows to an Excel tab and a separate CSV file.
    used_names = {"00_Summary", "01_Mapping", "02_Helpers", "03_Signoff"}
    for i, item in enumerate(result.metrics, start=1):
        sheet = _slug_sheet(i, item.spec.metric_id or item.spec.name)
        base = sheet
        n = 2
        while sheet in used_names:
            sheet = (base[:28] + f"_{n}")[:31]
            n += 1
        used_names.add(sheet)
        item.sheet_name = sheet
        csv_name = f"{i:02d}_{item.spec.metric_id}.csv"
        item.csv_filename = csv_name

        ws = wb.create_sheet(sheet)
        meta = [
            ("Metric", item.spec.name),
            ("Chart", item.spec.chart),
            ("SQL expression", item.spec.combined_expression()),
            ("Kind", item.spec.kind),
            ("CSV value", item.csv_value),
            ("Dashboard value", item.dashboard_value),
            ("Status", item.status),
            ("Patient rows below", len(item.patient_ids)),
            ("Proof", "Count the data rows below; it must equal CSV value"),
        ]
        for row in meta:
            ws.append(list(row))
            ws.cell(ws.max_row, 1).fill = META_FILL
            ws.cell(ws.max_row, 1).font = Font(bold=True)
        ws.append([])

        frame = _metric_frame(df, item.patient_ids, id_column, item.used_columns, config)
        frame.to_csv(csv_dir / csv_name, index=False, encoding="utf-8-sig")
        for r_i, row in enumerate(dataframe_to_rows(frame, index=False, header=True), start=1):
            ws.append(list(row))
            if r_i == 1:
                _style_header(ws, ws.max_row)
        ws.append([])
        ws.append(["ROW_COUNT", len(frame), "Must equal CSV value", item.csv_value])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
        _autosize(ws)
