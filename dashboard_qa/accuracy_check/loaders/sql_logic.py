"""Finds the separate counts and totals described by the dashboard SQL."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from accuracy_check.models import MetricSpec

CHART_RE = re.compile(r"^\s*(?:#|--)?\s*Chart:\s*(.+?)\s*$", re.I | re.M)
QUERY_RE = re.compile(r"^\s*(?:#|--)?\s*(Query(?:\s+\d+)?)\s*:\s*$", re.I | re.M)
SELECT_RE = re.compile(r"\bselect\b", re.I)
FROM_RE = re.compile(r"\bfrom\b", re.I)
WHERE_RE = re.compile(r"\bwhere\b", re.I)
GROUP_RE = re.compile(r"\bgroup\s+by\b", re.I)

IGNORE_WHERE_RE = re.compile(
    r"""
    (?:
        \bEVENT_ID\b
        |\bTN_ID\b
        |\b[ab]\.TN_ID\b
        |\bLOC_
        |\bR_ID\b
        |\bR_LocID\b
        |\bEVENT_
        |\b\$\{
    )
    """,
    re.I | re.VERBOSE,
)

# Patterns used to recognise labels, counts and sums in common BI query layouts.
LABEL_WHEN_RE = re.compile(
    r"when\s+(\d+)\s+then\s+'([^']*)'",
    re.I,
)
WHEN_THEN_RE = re.compile(r"when\s+(\d+)\s+then\s+", re.I)
COUNT_AS_RE = re.compile(
    r"count\s*\(\s*([^)]+?)\s*\)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.I,
)
SUM_AS_RE = re.compile(
    r"sum\s*\(\s*(.*?)\s*\)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.I | re.S,
)
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def load_sql_text(path: Path) -> str:
    # Supports SQL supplied as a plain file or copied into a Word document.
    suffix = path.suffix.lower()
    if suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    return path.read_text(encoding="utf-8-sig")


def _balanced_from(text: str, open_idx: int) -> tuple[str, int]:
    """open_idx points at '('."""
    depth = 0
    for i in range(open_idx, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : i], i + 1
    raise ValueError("Unbalanced parentheses in SQL")


def _looks_boolean(expr: str) -> bool:
    lowered = expr.lower()
    return any(
        token in lowered
        for token in ("=", ">", "<", " between ", " is ", " and ", " or ", " in ", " not ")
    )


def _strip_sql_comments_keep_headers(text: str) -> str:
    # Removes notes while retaining Chart and Query labels used in the report.
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if CHART_RE.match(stripped) or QUERY_RE.match(stripped):
            lines.append(stripped)
            continue
        if stripped.startswith("#") or stripped.startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _split_statements(text: str) -> list[tuple[str, str, str]]:
    """Separates the file into queries and keeps the chart name for each one."""
    prepared = _strip_sql_comments_keep_headers(text)
    chart = "Headline KPIs"
    query_label = ""
    statements: list[tuple[str, str, str]] = []

    matches = list(SELECT_RE.finditer(prepared))
    headers = []
    for m in CHART_RE.finditer(prepared):
        headers.append((m.start(), "chart", m.group(1).strip()))
    for m in QUERY_RE.finditer(prepared):
        headers.append((m.start(), "query", m.group(1).strip()))
    headers.sort()

    def header_at(pos: int) -> tuple[str, str]:
        c, q = chart, query_label
        for start, kind, value in headers:
            if start > pos:
                break
            if kind == "chart":
                c, q = value, ""
            else:
                q = value
        return c, q

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prepared)
        block = prepared[start:end].strip()
        if block.endswith(";"):
            block = block[:-1].strip()
        c, q = header_at(start)
        statements.append((c, q, block))
    return statements


def _select_body(statement: str) -> tuple[str, str, str]:
    sm = SELECT_RE.search(statement)
    fm = FROM_RE.search(statement)
    if not sm or not fm or fm.start() < sm.end():
        return statement, "", ""
    select_list = statement[sm.end() : fm.start()]
    rest = statement[fm.start() :]
    wm = WHERE_RE.search(rest)
    if not wm:
        return select_list, "", rest
    after_where = rest[wm.end() :]
    gm = GROUP_RE.search(after_where)
    where = after_where[: gm.start()] if gm else after_where
    return select_list, where, rest


def _split_where_clauses(where: str) -> list[str]:
    if not where.strip():
        return []
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    tokens = re.split(r"(\band\b)", where, flags=re.I)
    for tok in tokens:
        if re.fullmatch(r"and", tok, re.I) and depth == 0:
            clause = "".join(buf).strip()
            if clause:
                parts.append(clause)
            buf = []
            continue
        depth += tok.count("(") - tok.count(")")
        buf.append(tok)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _patient_where(where: str) -> str:
    # Keeps patient filters but removes database joins and event controls already fixed by the export.
    keep = []
    for clause in _split_where_clauses(where):
        cleaned = clause.strip().strip("()")
        if IGNORE_WHERE_RE.search(cleaned):
            continue
        if re.fullmatch(r"\d+", cleaned):
            continue
        keep.append(cleaned)
    if not keep:
        return ""
    if len(keep) == 1:
        return keep[0]
    return " and ".join(f"({k})" for k in keep)


def _label_maps(select_list: str) -> list[dict[int, str]]:
    """Each CASE ... END that contains string labels becomes one dimension map."""
    maps: list[dict[int, str]] = []
    current: dict[int, str] = {}
    token_re = re.compile(r"when\s+(\d+)\s+then\s+'([^']*)'|\bend\b", re.I)
    for m in token_re.finditer(select_list):
        if m.group(0).lower().lstrip().startswith("end"):
            if current:
                maps.append(current)
                current = {}
            continue
        current[int(m.group(1))] = m.group(2)
    if current:
        maps.append(current)
    return maps


def _previous_when(text: str, idx: int) -> Optional[int]:
    window = text[max(0, idx - 80) : idx]
    matches = list(WHEN_THEN_RE.finditer(window))
    if not matches:
        return None
    return int(matches[-1].group(1))


def _parse_inner_case(inner: str) -> list[tuple[int, str]]:
    text = inner.strip()
    if text.lower().startswith("case"):
        text = text[4:].strip()
    pairs: list[tuple[int, str]] = []
    for m in WHEN_THEN_RE.finditer(text):
        start = m.end()
        nxt = WHEN_THEN_RE.search(text, start)
        end_m = re.search(r"\bend\b", text[start:], re.I)
        end = len(text)
        if nxt:
            end = min(end, nxt.start())
        if end_m:
            end = min(end, start + end_m.start())
        expr = text[start:end].strip().rstrip(",").strip()
        if expr:
            pairs.append((int(m.group(1)), expr))
    return pairs


def _slug(parts: list[str]) -> str:
    raw = "_".join(p for p in parts if p)
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")
    return cleaned[:80] or "metric"


def extract_metrics(sql_text: str) -> list[MetricSpec]:
    # Converts each recognised count, sum or CASE-grid cell into one checkable metric.
    metrics: list[MetricSpec] = []
    seen: set[str] = set()

    for chart, query_label, statement in _split_statements(sql_text):
        select_list, where, _rest = _select_body(statement)
        where_extra = _patient_where(where)
        maps = _label_maps(select_list)
        dim1 = maps[0] if maps else {}
        dim2 = maps[1] if len(maps) > 1 else {}

        for m in COUNT_AS_RE.finditer(select_list):
            alias = m.group(2)
            col = m.group(1).strip()
            expr = "TRUE" if col == "*" else f"{col} is not null"
            mid = _slug([alias])
            if mid in seen:
                mid = _slug([chart, alias])
            seen.add(mid)
            metrics.append(
                MetricSpec(
                    metric_id=mid,
                    name=alias,
                    chart=chart,
                    expression=expr,
                    kind="count",
                    sql_alias=alias,
                    query_label=query_label,
                    where_extra=where_extra,
                    source_sql=statement[:400],
                )
            )

        # Handles a single named sum outside a chart grid.
        for m in SUM_AS_RE.finditer(select_list):
            inner = m.group(1).strip()
            alias = m.group(2)
            if inner.lower().startswith("case"):
                continue
            if " when " in inner.lower():
                continue
            kind = "count" if _looks_boolean(inner) else "sum"
            mid = _slug([alias])
            if mid in seen:
                mid = _slug([chart, alias])
            seen.add(mid)
            metrics.append(
                MetricSpec(
                    metric_id=mid,
                    name=alias,
                    chart=chart,
                    expression=inner,
                    kind=kind,
                    sql_alias=alias,
                    query_label=query_label,
                    where_extra=where_extra,
                    source_sql=statement[:400],
                )
            )

        # Expands chart grids so every age, sex or cohort cell receives its own check.
        search_from = 0
        lower = select_list.lower()
        while True:
            idx = lower.find("sum(", search_from)
            if idx < 0:
                break
            try:
                inner, end = _balanced_from(select_list, idx + 3)
            except ValueError:
                break
            search_from = end
            outer_when = _previous_when(select_list, idx)
            inner_stripped = inner.strip()

            cells: list[tuple[Optional[int], Optional[int], str]] = []
            if inner_stripped.lower().startswith("case") or WHEN_THEN_RE.search(inner_stripped):
                for inner_when, expr in _parse_inner_case(inner_stripped):
                    cells.append((outer_when, inner_when, expr))
            else:
                # Avoid double-counting sum(...) as Alias already captured
                after = select_list[end : end + 40]
                if re.match(r"\s+as\s+", after, re.I) and not outer_when:
                    continue
                cells.append((outer_when, None, inner_stripped))

            for outer_w, inner_w, expr in cells:
                labels: dict[str, str] = {}
                name_parts = [chart]
                if query_label:
                    name_parts.append(query_label)
                if outer_w is not None and dim2:
                    labels["series"] = dim2.get(outer_w, str(outer_w))
                    name_parts.append(labels["series"])
                elif outer_w is not None and dim1 and not dim2:
                    labels["category"] = dim1.get(outer_w, str(outer_w))
                    name_parts.append(labels["category"])
                if inner_w is not None and dim1:
                    labels["category"] = dim1.get(inner_w, str(inner_w))
                    name_parts.append(labels["category"])
                elif inner_w is not None and dim2 and outer_w is None:
                    labels["series"] = dim2.get(inner_w, str(inner_w))
                    name_parts.append(labels["series"])
                if len(name_parts) == 1:
                    name_parts.append(expr[:40])
                name = " · ".join(name_parts)
                mid = _slug(name_parts)
                n = 2
                original = mid
                while mid in seen:
                    mid = f"{original}_{n}"
                    n += 1
                seen.add(mid)
                kind = "count" if _looks_boolean(expr) else "sum"
                metrics.append(
                    MetricSpec(
                        metric_id=mid,
                        name=name,
                        chart=chart,
                        expression=expr.strip(),
                        kind=kind,
                        sql_alias="",
                        query_label=query_label,
                        where_extra=where_extra,
                        labels=labels,
                        source_sql=statement[:400],
                    )
                )

    return metrics
