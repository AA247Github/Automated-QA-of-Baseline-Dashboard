"""Runs the full check from source files through to the evidence pack."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from accuracy_check.config import AppConfig
from accuracy_check.engine.compare import apply_dashboard_values
from accuracy_check.engine.expressions import ExpressionEngine
from accuracy_check.engine.helpers import run_helper_check
from accuracy_check.engine.replicate import ColumnResolver, replicate_metric
from accuracy_check.loaders.csv_data import load_cliics_csv
from accuracy_check.loaders.dashboard_pdf import extract_pdf_text
from accuracy_check.loaders.mapping import load_mapping, match_csv_header
from accuracy_check.loaders.sql_logic import extract_metrics, load_sql_text
from accuracy_check.models import (
    FileFingerprint,
    HelperCheckSpec,
    InputPaths,
    MetricSpec,
    RunResult,
)
from accuracy_check.outputs.evidence import write_evidence
from accuracy_check.outputs.report import write_json_result, write_markdown_report


def _fingerprint(path: Path) -> FileFingerprint:
    # Records a digital fingerprint so the checked file version can be proven later.
    data = path.read_bytes()
    return FileFingerprint(
        path=str(path),
        sha256=hashlib.sha256(data).hexdigest(),
        bytes=len(data),
    )


def _find_id_column(df: pd.DataFrame, mapping: dict[str, str]) -> str:
    # Finds the patient identifier used to list supporting rows in the evidence.
    for candidate in ("ID", "Id", "Patient ID", "PatientID"):
        hit = match_csv_header(candidate, list(df.columns))
        if hit:
            return hit
    preferred = [k for k in mapping if k.endswith("_PatientID")]
    preferred += [k for k in mapping if k.endswith("_ID") and k not in preferred]
    for sql_name in preferred:
        hit = match_csv_header(mapping[sql_name], list(df.columns))
        if hit:
            return hit
    return str(df.columns[0])


def _apply_identity_fallbacks(mapping: dict[str, str]) -> dict[str, str]:
    # Covers SQL that counts a row ID when the mapping only names the patient ID.
    out = dict(mapping)
    for sql_name, csv_name in list(out.items()):
        if sql_name.endswith("_PatientID"):
            out.setdefault(f"{sql_name[:-10]}_ID", csv_name)
    return out


def run_accuracy_check(
    inputs: InputPaths,
    config: AppConfig,
    output_dir: Path,
    context: dict | None = None,
) -> RunResult:
    # Stop early if the three files needed for internal calculations are missing.
    missing = [
        label
        for label, path in (
            ("CSV", inputs.csv),
            ("SQL", inputs.sql),
            ("mapping", inputs.mapping),
        )
        if path is None
    ]
    if missing:
        raise FileNotFoundError(
            "Missing required inputs: "
            + ", ".join(missing)
            + ". Place CLIICS_Upload.csv, a .sql (or SQL .docx), and a mapping .xlsx in the folder."
        )

    # Load the source data, field mapping and individual calculations from SQL.
    df, csv_info = load_cliics_csv(inputs.csv)
    mapping = _apply_identity_fallbacks(load_mapping(inputs.mapping))
    sql_text = load_sql_text(inputs.sql)
    metrics = extract_metrics(sql_text)

    # Add any service-specific calculations declared outside the SQL file.
    for extra in config.extra_metrics:
        metrics.append(
            MetricSpec(
                metric_id=extra.get("id", extra.get("name", "extra")),
                name=extra.get("name", extra.get("id", "extra")),
                chart=extra.get("chart", "Configured extras"),
                expression=extra.get("expression", "TRUE"),
                kind=extra.get("kind", "count"),
                sql_alias=extra.get("alias", ""),
                where_extra=extra.get("where", ""),
            )
        )

    # Prepare the source rows and calculation engine.
    pdf_text = extract_pdf_text(inputs.pdf) if inputs.pdf else ""
    id_column = _find_id_column(df, mapping)
    resolver = ColumnResolver(df, mapping)
    engine = ExpressionEngine(df, resolver.resolve, config.value_maps)
    id_series = df[id_column]

    # Rebuild each SQL figure from the CSV, then compare it with the PDF.
    results = [replicate_metric(spec, engine, resolver, id_series) for spec in metrics]
    if pdf_text:
        apply_dashboard_values(results, pdf_text, config.dashboard_labels)

    # Run extra consistency checks supplied by the selected service profile.
    helpers = []
    for raw in config.helper_checks:
        spec = HelperCheckSpec(
            check_id=raw.get("id", raw.get("name", "check")),
            name=raw.get("name", raw.get("id", "check")),
            left=raw["left"],
            right=raw["right"],
            description=raw.get("description", ""),
            kind=raw.get("kind", "equivalent"),
        )
        helpers.append(run_helper_check(spec, engine, id_series))

    # Capture the exact input versions and notes used by the audit trail.
    fingerprints = [
        _fingerprint(path)
        for path in (inputs.csv, inputs.sql, inputs.pdf, inputs.mapping, inputs.profile)
        if path and path.exists()
    ]

    notes = list(config.notes)
    notes.append(
        f"CSV {inputs.csv.name}: {csv_info['n_rows']} data rows, "
        f"{csv_info['n_columns']} columns, header row {csv_info['header_row']}."
    )
    if csv_info.get("metadata"):
        notes.append("CSV metadata: " + " | ".join(csv_info["metadata"][:4]))
    if inputs.pdf is None:
        notes.append("No dashboard PDF found — CSV replication only.")

    # Package all results once so every output uses the same information.
    run = RunResult(
        inputs=inputs,
        fingerprints=fingerprints,
        metrics=results,
        helpers=helpers,
        mapping=mapping,
        unmapped_sql=sorted(set(resolver.unmapped)),
        pdf_text=pdf_text,
        notes=notes,
        extras={"csv_info": csv_info, "id_column": id_column, **(context or {})},
    )

    # Write the workbook, filtered CSV files, written report and machine result.
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "QA_Evidence.xlsx"
    csv_dir = output_dir / "evidence_csvs"
    write_evidence(run, df, id_column, config, evidence_path, csv_dir)
    write_markdown_report(run, output_dir / "QA_Report.md")
    write_json_result(run, output_dir / "QA_Results.json")
    return run
