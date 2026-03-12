from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from textmystery.interfaces.live_contract import leak_check, parity_check


class _Handler(BaseHTTPRequestHandler):
    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b"{}"
        parsed = json.loads(body.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._write_json(400, {"error": "invalid_json"})
            return

        if self.path == "/textmystery/parity-check":
            self._write_json(200, parity_check(payload))
            return
        if self.path == "/textmystery/leak-check":
            self._write_json(200, leak_check(payload))
            return
        self._write_json(404, {"error": "not_found"})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="TextMystery local live contract server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
