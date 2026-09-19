"""Matches calculated values to figures found in the dashboard printout."""

from __future__ import annotations

from collections import Counter

from accuracy_check.loaders.dashboard_pdf import find_labelled_number, number_present
from accuracy_check.models import MetricResult


def apply_dashboard_values(
    metrics: list[MetricResult],
    pdf_text: str,
    label_map: dict[str, list[str]],
) -> None:
    # First use nearby labels to connect headline figures to their calculation.
    # Metrics that already failed to compute a CSV value (status == "ERROR",
    # e.g. a SQL expression the engine couldn't parse) have nothing real to
    # match against — attaching a PDF number to them anyway is misleading
    # noise in the evidence pack (a broken metric would still show a
    # confident-looking "Dashboard value"), so they're skipped here too, not
    # only when the final status is assigned below.
    for result in metrics:
        if result.status == "ERROR":
            continue
        aliases = _aliases_for(result, label_map)
        value, evidence = find_labelled_number(pdf_text, aliases, expected=result.csv_value)
        if value is not None:
            result.dashboard_value = float(value)
            result.pdf_evidence = evidence

    # Records whether each calculated number is unique across the SQL metrics.
    value_freq = Counter(
        int(r.csv_value) for r in metrics if r.csv_value is not None
    )

    # A unique number found in the PDF can be linked even without a clear label.
    for result in metrics:
        if result.dashboard_value is not None or result.csv_value is None:
            continue
        as_int = int(result.csv_value)
        unique = value_freq[as_int] == 1
        if unique and number_present(pdf_text, as_int):
            result.dashboard_value = float(as_int)
            result.pdf_evidence = (
                f"{as_int} is unique among SQL metrics and appears on the dashboard printout"
            )

    # Assigns the final status used on screen and in the evidence pack.
    for result in metrics:
        if result.status == "ERROR":
            continue
        if result.dashboard_value is None:
            result.status = "CSV_ONLY"
            if result.csv_value is not None and number_present(pdf_text, result.csv_value):
                result.pdf_evidence = (
                    f"{int(result.csv_value)} appears on the printout but is not unique enough "
                    "to auto-match; confirm on the evidence sheet"
                )
            continue
        if result.csv_value is None:
            result.status = "ERROR"
            continue
        if int(result.csv_value) == int(result.dashboard_value):
            result.status = "MATCH"
        else:
            result.status = "MISMATCH"


def _aliases_for(result: MetricResult, label_map: dict[str, list[str]]) -> list[str]:
    # Collects the possible names used for the same metric in SQL and the PDF.
    spec = result.spec
    aliases: list[str] = []
    aliases.extend(label_map.get(spec.metric_id, []))
    aliases.extend(label_map.get(spec.sql_alias, []))
    aliases.extend(label_map.get(spec.name, []))
    if spec.sql_alias:
        aliases.append(_title_case_alias(spec.sql_alias))
        aliases.append(spec.sql_alias)
    # Chart title only for headline metrics (no age/sex/cohort crumb labels)
    if spec.chart and not spec.labels:
        aliases.append(spec.chart)
    # de-dupe, keep order
    seen = set()
    out = []
    for a in aliases:
        key = a.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(a.strip())
    return out


def _title_case_alias(alias: str) -> str:
    # Makes SQL names such as PatientsIdentified easier to match with printed text.
    spaced = "".join(c if c.islower() else f" {c}" for c in alias).strip()
    return spaced
