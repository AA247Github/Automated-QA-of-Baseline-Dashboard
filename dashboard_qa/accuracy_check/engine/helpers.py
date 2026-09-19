"""Checks whether related helper columns agree as expected."""

from __future__ import annotations

from accuracy_check.engine.expressions import ExpressionEngine
from accuracy_check.models import HelperCheckSpec, HelperResult
import pandas as pd


def run_helper_check(
    spec: HelperCheckSpec,
    engine: ExpressionEngine,
    id_series: pd.Series,
) -> HelperResult:
    try:
        # Evaluates both rules against the same patient rows.
        left = engine.eval_bool(spec.left).fillna(False)
        right = engine.eval_bool(spec.right).fillna(False)
        left_only = left & ~right
        right_only = right & ~left
        both = left & right
        neither = ~left & ~right
        if spec.kind == "implies":
            # For an implication, only rows meeting the left rule can fail.
            mismatch = left_only
        else:
            mismatch = left_only | right_only
        # Keeps example patient IDs so exceptions can be reviewed.
        ids = [str(v) for v in id_series.loc[mismatch].tolist() if str(v).strip()]
        n = int(mismatch.sum())
        return HelperResult(
            spec=spec,
            mismatches=n,
            left_only=int(left_only.sum()),
            right_only=int(right_only.sum()),
            both=int(both.sum()),
            neither=int(neither.sum()),
            mismatch_ids=ids[:200],
            status="PASS" if n == 0 else "FAIL",
        )
    except Exception as exc:
        # Returns the failure as evidence instead of stopping every other check.
        return HelperResult(
            spec=spec,
            mismatches=-1,
            left_only=0,
            right_only=0,
            both=0,
            neither=0,
            status="ERROR",
            error=str(exc),
        )
