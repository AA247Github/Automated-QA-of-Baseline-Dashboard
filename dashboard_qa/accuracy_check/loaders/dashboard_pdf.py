"""Read dashboard printouts and locate numbers next to metric labels."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

NUMBER_RE = re.compile(r"(?<![\w.])(\d{1,7})(?![\w.])")

# A number immediately followed by "%" (allowing for the odd stray space that
# PDF text extraction sometimes inserts) is a percentage, never the count we
# want to match against a CSV replication. This dashboard's KPI tiles mix
# "95% (325 of 341) ..." and "16 (5%) patients ..." freely — the percentage
# sits on either side of the real count — so order alone can't tell them
# apart, but "is this number immediately glued to a %" always can.
PERCENT_SUFFIX_RE = re.compile(r"^\s{0,2}%")


def is_plausible_count(value: int) -> bool:
    """Drop report years, job codes and other non-count figures."""
    if value >= 1900 and value <= 2100:
        return False
    if value > 100_000:
        return False
    return True


def extract_pdf_text(path: Path) -> str:
    # Combines the readable text from every dashboard page.
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _normalise_text(text: str) -> str:
    text = text.replace(" ", " ")
    # Dashboard KPI labels routinely wrap across a line inside the PDF (e.g.
    # "...have a record of at \nleast one objective \ntest"). Collapsing
    # newlines to spaces (like the CSV/mapping loaders already do for
    # headers) lets a multi-word dashboard_labels phrase match text that was
    # only ever split by page layout, not by real punctuation.
    text = re.sub(r"[ \t\r\n]+", " ", text)
    return text


def extract_integers(text: str, *, exclude_percentages: bool = True) -> list[int]:
    # exclude_percentages=True drops any number immediately followed by "%",
    # since that is always a rate/percentage, never a raw count — see
    # PERCENT_SUFFIX_RE above. Kept as an opt-out for any caller that
    # genuinely wants percentages too (none currently do).
    out = []
    for m in NUMBER_RE.finditer(text):
        if exclude_percentages and PERCENT_SUFFIX_RE.match(text[m.end() : m.end() + 2]):
            continue
        out.append(int(m.group(1)))
    return out


def _alias_windows(haystack: str, needle: str) -> list[str]:
    # Takes short sections around a dashboard label where its value is likely shown.
    h = haystack.lower()
    n = needle.lower().strip()
    if not n:
        return []
    indexes = [m.start() for m in re.finditer(re.escape(n), h)]
    if not indexes:
        tokens = [t for t in re.split(r"\s+", n) if t not in {"the", "for", "of", "in", "and", "by"}]
        if len(tokens) >= 3 and all(t in h for t in tokens):
            indexes = [min(h.find(t) for t in tokens)]
    windows = []
    for idx in indexes:
        # Prefer text after the label — KPI titles sit above the figure
        windows.append(h[idx : idx + len(n) + 220])
        windows.append(h[max(0, idx - 40) : idx + len(n) + 80])
    return windows


def find_labelled_number(
    text: str,
    aliases: list[str],
    expected: int | float | None = None,
) -> tuple[int | None, str]:
    # Prefers the expected CSV value when several numbers sit near the same label.
    compact = _normalise_text(text)
    found: list[int] = []
    used_alias = ""
    for alias in aliases:
        for window in _alias_windows(compact, alias):
            nums = [n for n in extract_integers(window) if is_plausible_count(n)]
            if nums:
                found.extend(nums)
                used_alias = used_alias or alias
    if expected is not None:
        try:
            exp = int(expected)
        except (TypeError, ValueError):
            exp = None
        if exp is not None and exp in found:
            return exp, f"{exp} appears near {used_alias!r} on the dashboard printout"
    if found:
        return found[0], f"Found {found[0]} near {used_alias!r}"
    return None, ""


def number_present(text: str, value: int | float | None) -> bool:
    # Confirms that a whole-number result appears anywhere in the printout text
    # as a genuine count, not as part of a percentage figure.
    if value is None:
        return False
    as_int = int(value)
    if as_int != value:
        return False
    pattern = re.compile(rf"(?<![\w.]){as_int}(?![\w.])")
    for m in pattern.finditer(text):
        if not PERCENT_SUFFIX_RE.match(text[m.end() : m.end() + 2]):
            return True
    return False
