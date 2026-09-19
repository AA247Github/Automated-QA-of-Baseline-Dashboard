# Dashboard Accuracy Check

A local tool for QA-checking a clinical service dashboard: it takes the same
CSV extract, SQL logic and column mapping the dashboard was built from,
independently replicates every metric the SQL calculates, and — when you
also supply the published dashboard PDF — cross-checks each replicated
number against what the dashboard actually prints. The result is a
downloadable evidence pack (spreadsheet, markdown report and JSON) you can
attach to a QA sign-off.

It ships as a small local web app (Flask) that runs entirely on your own
machine — nothing is uploaded anywhere outside `outputs/web_runs/`.

## What it does

1. **Loads the CLIICS CSV export**, auto-detecting the metadata/header rows
   CLIICS exports typically include.
2. **Reads the dashboard's SQL** (a plain `.sql` file, or SQL pasted into a
   `.docx`) and extracts each count/sum it calculates as an individually
   checkable metric.
3. **Loads the SQL↔CSV column mapping workbook** so each SQL field can be
   resolved to the matching CSV header.
4. **Replicates every metric directly against the CSV** using a small,
   restricted SQL-expression engine (comparisons, `AND`/`OR`/`NOT`,
   `BETWEEN`, `IN`, `IS [NOT] NULL`), including Y/N ↔ 1/0 and
   Male/Female ↔ 1/2 style value normalisation.
5. **Matches each replicated number against the dashboard PDF** (optional),
   using labelled-text proximity search plus a "value is unique among all
   metrics" fallback, so each row ends up `MATCH`, `MISMATCH`, `CSV_ONLY`
   (no confident match found) or `ERROR`.
6. **Runs configurable helper checks** — cross-column consistency rules
   (e.g. "authorised patients must be in a clinical cohort") defined per
   service, independent of the dashboard SQL.
7. **Writes an evidence pack**: `QA_Evidence.xlsx` (one sheet per metric,
   plus summary/mapping/helpers/sign-off sheets), `QA_Report.md`,
   `QA_Results.json`, and a `QA_Pack.zip` bundling all three with the
   original inputs.

## Project structure

```
.
├── run_ui.py                     # Launches the local web UI (start here)
├── run_ui.bat                    # Windows double-click launcher
├── dashboard_qa/
│   ├── webapp.py                 # Flask app: upload form, run pipeline, downloads
│   ├── web/templates/index.html  # Upload/results page
│   ├── requirements.txt
│   └── accuracy_check/
│       ├── config.py             # Loads a service profile (or generic defaults)
│       ├── models.py             # Shared dataclasses (MetricSpec, RunResult, ...)
│       ├── pipeline.py           # Orchestrates load → replicate → compare → write
│       ├── run_support.py        # Profile listing/auto-detect, run summarising
│       ├── loaders/
│       │   ├── csv_data.py       # CLIICS CSV loader
│       │   ├── sql_logic.py      # Dashboard SQL → list of checkable metrics
│       │   ├── mapping.py        # SQL↔CSV column mapping workbook loader
│       │   └── dashboard_pdf.py  # Dashboard PDF text extraction + number matching
│       ├── engine/
│       │   ├── expressions.py    # Restricted SQL-expression parser/evaluator
│       │   ├── replicate.py      # Runs one MetricSpec against the CSV
│       │   ├── compare.py        # Matches replicated values to the PDF
│       │   └── helpers.py        # Runs helper_checks from the profile
│       ├── outputs/
│       │   ├── evidence.py       # Builds QA_Evidence.xlsx
│       │   └── report.py         # Builds QA_Report.md / QA_Results.json
│       └── profiles/
│           ├── oab_baseline.yaml       # Example: Pierre Fabre OAB service
│           └── chiesi_asthma.yaml      # Example: Chiesi Asthma service
└── outputs/
    └── web_runs/                 # One timestamped folder per run (git-ignored)
```

## Requirements

- Python 3.10+
- `pip install -r dashboard_qa/requirements.txt`
  (pandas, openpyxl, PyYAML, pypdf, python-docx, Flask)

## Usage

```bash
python run_ui.py
```

This opens `http://127.0.0.1:8765` in your browser (or double-click
`run_ui.bat` on Windows). From there:

1. Upload the CLIICS CSV export, the dashboard `.sql` (or `.docx`), and the
   SQL↔CSV mapping `.xlsx`. Optionally upload the dashboard PDF too — without
   it, metrics are still replicated from the CSV, they just can't be
   verified against a published figure.
2. Enter a service name / therapy area (used for profile auto-detection),
   or pick a profile from the dropdown directly. "Generic" runs with no
   service-specific rules at all.
3. Run the check. The page shows a live summary (match/mismatch/unverified
   counts); download links for the full evidence pack appear alongside it.

## Service profiles

A profile is a YAML file in `accuracy_check/profiles/` that tailors the
generic engine to one service's dashboard: which CSV columns to always
surface on the evidence sheet, the phrases used to find each metric in the
dashboard PDF, and any extra cross-column consistency checks. See
`oab_baseline.yaml` for a fully worked example. Adding a new service is just
adding a new YAML file here — no code changes required — with these keys:

| Key | Purpose |
|---|---|
| `name` | Display name shown in the profile dropdown |
| `match_keywords` | Words that trigger Auto-detect for this profile |
| `evidence_mode` / `always_include_columns` | Which CSV columns appear on every evidence sheet |
| `dashboard_labels` | Maps a metric's ID/SQL alias/name to the phrase(s) used near it in the dashboard PDF |
| `helper_checks` | Cross-column consistency rules (`left`/`right` SQL-style expressions, `equivalent` or `implies`) |
| `notes` | Free-text interpretation notes carried into the generated report |

## Output files

- **`QA_Evidence.xlsx`** — `00_Summary` (every metric, its SQL expression,
  replicated CSV value, matched dashboard value and status),
  `01_Mapping`, `02_Helpers`, `03_Signoff`, plus one sheet per metric with
  the supporting patient-level rows.
- **`QA_Report.md`** — a narrative summary of the same run.
- **`QA_Results.json`** — the same data, machine-readable.
- **`QA_Pack.zip`** — all of the above plus the original uploaded inputs,
  for audit purposes.

## Known limitations

- Dashboard PDF matching relies on text extraction quality (`pypdf`); keep
  it on a recent version (`>=4.0`, ideally 5.x/6.x) — older versions can
  merge adjacent numbers in dense charts with no separating whitespace.
- A metric only auto-matches to the PDF without an explicit
  `dashboard_labels` entry if its replicated value is numerically unique
  across *all* metrics in the run — anything that repeats (very common with
  small patient cohorts) needs a label to disambiguate.
- The SQL parser handles a common subset of dashboard-report SQL (named
  `COUNT`/`SUM` aliases, `CASE WHEN` grids); more exotic constructs (nested
  ratios, window functions) may not extract as a checkable metric at all.

