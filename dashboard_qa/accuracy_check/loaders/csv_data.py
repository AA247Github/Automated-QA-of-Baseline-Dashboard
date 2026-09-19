"""Load a CLIICS generate-CSV export, including the metadata header row."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pandas as pd


def _norm_header(value: str) -> str:
    # Removes line breaks and uneven spacing from spreadsheet headings.
    return re.sub(r"\s+", " ", str(value).replace("\n", " ").replace("\r", " ")).strip()


def _looks_metadata_row(row: list[str]) -> bool:
    # Identifies the file/version line placed above headings in CLIICS exports.
    filled = [c for c in row if str(c).strip()]
    if not filled:
        return True
    blob = " ".join(str(c) for c in filled[:4]).lower()
    if any(token in blob for token in (".xls", ".csv", "v0", "emis", "systm", "tpp", ":\\", "emis web")):
        return True
    return False


def _looks_header_row(row: list[str]) -> bool:
    # Uses common patient fields to recognise the real heading row.
    joined = " ".join(_norm_header(c) for c in row).lower()
    return "age" in joined and ("id" in joined or "gender" in joined or "sex" in joined)


# Tried in order. utf-8-sig handles plain UTF-8 exports (and strips a BOM if
# present). CLIICS exports from EMIS/SystmOne/TPP are frequently Windows-1252
# instead (e.g. superscript units in spirometry/respiratory columns), which
# is not valid UTF-8 and would otherwise raise UnicodeDecodeError partway
# through the file. latin-1 is listed last as a catch-all: every byte value
# maps to a character in latin-1, so it never raises, but it's tried last
# because it would silently "succeed" on a genuinely Windows-1252 file too,
# just decoding a handful of characters (e.g. curly quotes, en/em dashes)
# incorrectly.
_ENCODINGS_TO_TRY = ("utf-8-sig", "cp1252", "latin-1")


def _read_rows(path: Path) -> list[list[str]]:
    # Reads the raw bytes once and tries each candidate encoding in turn,
    # rather than assuming the file is UTF-8. Some CLIICS exports (e.g. from
    # older EMIS/SystmOne/TPP installs) are Windows-1252, not UTF-8.
    raw = path.read_bytes()
    last_error: UnicodeDecodeError | None = None
    for encoding in _ENCODINGS_TO_TRY:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        return list(csv.reader(io.StringIO(text, newline="")))
    # latin-1 above never raises, so this is unreachable in practice, but
    # keeps the original failure visible if that ever changes.
    raise last_error  # pragma: no cover


def load_cliics_csv(path: Path) -> tuple[pd.DataFrame, dict]:
    # Reads the complete file before separating metadata, headings and patient rows.
    rows = _read_rows(path)
    if len(rows) < 2:
        raise ValueError(f"{path.name} does not contain a header and data")

    header_idx = 0
    metadata: list[str] = []
    if _looks_metadata_row(rows[0]) and len(rows) > 1:
        metadata = rows[0]
        header_idx = 1
        if not _looks_header_row(rows[1]) and len(rows) > 2 and _looks_header_row(rows[2]):
            header_idx = 2

    # Gives blank or repeated headings safe unique names.
    headers = [_norm_header(h) for h in rows[header_idx]]
    used: dict[str, int] = {}
    unique_headers = []
    for h in headers:
        key = h or f"__blank_{len(unique_headers)}"
        if key in used:
            used[key] += 1
            key = f"{key}__{used[key]}"
        else:
            used[key] = 1
        unique_headers.append(key)

    # Makes short rows the same width and ignores cells beyond the headings.
    data = []
    for row in rows[header_idx + 1 :]:
        if len(row) < len(unique_headers):
            row = row + [""] * (len(unique_headers) - len(row))
        data.append(row[: len(unique_headers)])

    df = pd.DataFrame(data, columns=unique_headers)
    # Removes completely empty lines left at the end of an export.
    nonempty = df.apply(lambda s: s.astype(str).str.strip().ne("").any(), axis=1)
    df = df.loc[nonempty].reset_index(drop=True)

    info = {
        "path": str(path),
        "header_row": header_idx + 1,
        "metadata": [str(x) for x in metadata if str(x).strip()],
        "n_columns": len(unique_headers),
        "n_rows": len(df),
    }
    return df, info
