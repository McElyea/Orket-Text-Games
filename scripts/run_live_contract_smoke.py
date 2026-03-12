from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import pytest
from http.server import ThreadingHTTPServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Reuse the live contract HTTP handler used by the CLI server.
from textmystery.cli.live_server import _Handler


def main() -> int:
    os.chdir(PROJECT_ROOT)

    host = "127.0.0.1"
    port = 8787
    server = ThreadingHTTPServer((host, port), _Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    os.environ["TEXTMYSTERY_RUN_LIVE"] = "1"
    os.environ["TEXTMYSTERY_ORKET_BASE_URL"] = f"http://{host}:{port}"

    try:
        # Run only live-marker tests.
        exit_code = pytest.main(["-q", "-m", "ts_live"])
        return int(exit_code)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2.0)


if __name__ == "__main__":
    raise SystemExit(main())
