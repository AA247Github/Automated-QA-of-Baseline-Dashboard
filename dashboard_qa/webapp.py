"""Local HTML front end for dashboard accuracy checks across any service."""

from __future__ import annotations

import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from accuracy_check.config import load_config
from accuracy_check.models import InputPaths
from accuracy_check.pipeline import run_accuracy_check
from accuracy_check.run_support import list_profiles, resolve_profile, summarise_run

# Locations used by the web page and its generated QA packs.
WEB_DIR = ROOT / "web"
RUNS_DIR = ROOT.parent / "outputs" / "web_runs"
ALLOWED_RUN = re.compile(r"^[A-Za-z0-9_\-]+$")

# Defines the local Flask site and limits the total upload size.
app = Flask(
    __name__,
    template_folder=str(WEB_DIR / "templates"),
    static_folder=str(WEB_DIR / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024


def _slug(value: str, fallback: str = "service") -> str:
    # Produces a safe short name for each run folder.
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value or "").strip("_").lower()
    return cleaned[:40] or fallback


def _save_upload(storage, dest: Path) -> Path:
    # Keeps a copy of each submitted source file with its QA evidence.
    dest.parent.mkdir(parents=True, exist_ok=True)
    storage.save(dest)
    return dest


def _zip_run(run_dir: Path) -> Path:
    # Bundles the complete result into one downloadable file.
    zip_path = run_dir / "QA_Pack.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in run_dir.rglob("*"):
            if path == zip_path or path.is_dir():
                continue
            zf.write(path, path.relative_to(run_dir).as_posix())
    return zip_path


@app.get("/")
def index():
    # Serves the upload and results page.
    return render_template("index.html")


@app.get("/api/profiles")
def api_profiles():
    # Supplies the profile choices shown in the page dropdown.
    return jsonify(list_profiles())


@app.post("/api/run")
def api_run():
    # Validates the uploads and collects the service details entered on screen.
    csv_file = request.files.get("csv_file")
    sql_file = request.files.get("sql_file")
    mapping_file = request.files.get("mapping_file")
    pdf_file = request.files.get("pdf_file")
    if not csv_file or not csv_file.filename:
        return jsonify({"error": "CLIICS upload CSV is required."}), 400
    if not sql_file or not sql_file.filename:
        return jsonify({"error": "Dashboard SQL file is required."}), 400
    if not mapping_file or not mapping_file.filename:
        return jsonify({"error": "Column mapping workbook is required."}), 400

    service_name = (request.form.get("service_name") or "").strip()
    therapy_area = (request.form.get("therapy_area") or "").strip()
    dashboard_type = (request.form.get("dashboard_type") or "").strip()
    profile_choice = request.form.get("profile") or "auto"
    full_rows = request.form.get("full_rows") == "1"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{stamp}_{_slug(service_name or therapy_area or 'service')}"
    run_dir = RUNS_DIR / run_id
    input_dir = run_dir / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)

    # Saves the uploaded files into an isolated folder for this run.
    csv_path = _save_upload(csv_file, input_dir / Path(csv_file.filename).name)
    sql_path = _save_upload(sql_file, input_dir / Path(sql_file.filename).name)
    mapping_path = _save_upload(mapping_file, input_dir / Path(mapping_file.filename).name)
    pdf_path = None
    if pdf_file and pdf_file.filename:
        pdf_path = _save_upload(pdf_file, input_dir / Path(pdf_file.filename).name)

    hints = " ".join(
        [
            service_name,
            therapy_area,
            dashboard_type,
            csv_path.name,
            sql_path.name,
            mapping_path.name,
            pdf_path.name if pdf_path else "",
        ]
    )
    # Uses a matching service profile when one exists; otherwise generic logic is used.
    profile = resolve_profile(profile_choice, hints)
    config = load_config(profile)
    if full_rows:
        config.evidence_mode = "full"

    inputs = InputPaths(
        folder=input_dir,
        csv=csv_path,
        sql=sql_path,
        pdf=pdf_path,
        mapping=mapping_path,
        profile=profile,
    )
    try:
        # Runs the same checking pipeline used by the command-line version.
        result = run_accuracy_check(
            inputs,
            config,
            run_dir,
            context={
                "service_name": service_name,
                "therapy_area": therapy_area,
                "dashboard_type": dashboard_type,
                "profile_name": config.name if profile else "Generic",
                "run_id": run_id,
            },
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    # Returns both the on-screen summary and links to the generated evidence.
    _zip_run(run_dir)
    payload = summarise_run(result)
    payload["run_id"] = run_id
    payload["downloads"] = {
        "evidence": f"/runs/{run_id}/QA_Evidence.xlsx",
        "report": f"/runs/{run_id}/QA_Report.md",
        "json": f"/runs/{run_id}/QA_Results.json",
        "zip": f"/runs/{run_id}/QA_Pack.zip",
    }
    return jsonify(payload)


@app.get("/runs/<run_id>/<path:filename>")
def download_run_file(run_id: str, filename: str):
    # Restricts downloads to files inside a valid result folder.
    if not ALLOWED_RUN.match(run_id):
        abort(404)
    run_dir = (RUNS_DIR / run_id).resolve()
    try:
        run_dir.relative_to(RUNS_DIR.resolve())
    except ValueError:
        abort(404)
    target = (run_dir / filename).resolve()
    try:
        target.relative_to(run_dir)
    except ValueError:
        abort(404)
    if not target.is_file():
        abort(404)
    return send_from_directory(run_dir, filename, as_attachment=True)


def main() -> None:
    # Supports starting the web application directly as well as through run_ui.py.
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    host = "127.0.0.1"
    port = 8765
    print(f"Dashboard accuracy check UI: http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
