"""Rebuilds each SQL metric from the uploaded CSV."""

from __future__ import annotations

from accuracy_check.engine.expressions import ExpressionEngine
from accuracy_check.loaders.mapping import match_csv_header
from accuracy_check.models import MetricResult, MetricSpec
import pandas as pd


class ColumnResolver:
    # Links SQL field names to the actual CSV headers and records missing links.
    def __init__(self, df: pd.DataFrame, sql_to_csv: dict[str, str]):
        self.df = df
        self.sql_to_csv = sql_to_csv
        self.cache: dict[str, str] = {}
        self.unmapped: list[str] = []

    def resolve(self, sql_name: str) -> str:
        # Uses the mapping first, then checks for a matching CSV header.
        if sql_name in self.cache:
            return self.cache[sql_name]
        mapped = self.sql_to_csv.get(sql_name)
        header = None
        if mapped:
            header = match_csv_header(mapped, list(self.df.columns))
        if header is None:
            header = match_csv_header(sql_name, list(self.df.columns))
        if header is None:
            self.unmapped.append(sql_name)
            raise KeyError(sql_name)
        self.cache[sql_name] = header
        return header


def replicate_metric(
    spec: MetricSpec,
    engine: ExpressionEngine,
    resolver: ColumnResolver,
    id_series: pd.Series,
) -> MetricResult:
    expr = spec.combined_expression()
    try:
        # Records which source columns should appear on this metric's evidence sheet.
        used_sql = engine.referenced_sql_columns(expr)
        used_csv = []
        for name in used_sql:
            try:
                used_csv.append(resolver.resolve(name))
            except KeyError:
                pass
        if spec.kind == "sum" and not _is_boolean_metric(spec):
            # Numeric metrics add source values; boolean metrics count matching rows.
            values = engine.eval_numeric(expr)
            csv_value = float(values.fillna(0).sum())
            mask = values.notna()
        else:
            mask = engine.eval_bool(expr)
            csv_value = float(mask.sum())
        # Keeps every contributing patient ID as proof of the calculation.
        ids = [str(v) for v in id_series.loc[mask].tolist() if str(v).strip()]
        return MetricResult(
            spec=spec,
            csv_value=csv_value,
            dashboard_value=None,
            status="REPLICATED",
            patient_ids=ids,
            used_columns=list(dict.fromkeys(used_csv)),
        )
    except Exception as exc:
        # One unsupported metric is reported without preventing the remaining checks.
        return MetricResult(
            spec=spec,
            csv_value=None,
            dashboard_value=None,
            status="ERROR",
            error=str(exc),
        )


def _is_boolean_metric(spec: MetricSpec) -> bool:
    # Distinguishes row-count rules from columns that should be added.
    expr = spec.expression.lower()
    return spec.kind == "count" or any(
        token in expr for token in ("=", ">", "<", " between ", " is ", " and ", " or ", " in ")
    )
