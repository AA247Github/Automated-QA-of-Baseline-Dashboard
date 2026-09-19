"""Open the HTML accuracy-check front end in a local browser."""

from __future__ import annotations

import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "dashboard_qa"
# Makes the bundled application available without installing it as a package.
sys.path.insert(0, str(ROOT))

from webapp import app, RUNS_DIR  # noqa: E402


def main() -> None:
    # Creates the results location, opens the page, then starts the local server.
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    url = "http://127.0.0.1:8765"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Dashboard accuracy check UI: {url}")
    app.run(host="127.0.0.1", port=8765, debug=False)


if __name__ == "__main__":
    main()
