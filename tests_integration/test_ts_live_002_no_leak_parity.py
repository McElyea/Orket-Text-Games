"""TS-LIVE-002: No-leak parity through Orket integration boundary. Milestone: M2."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

pytestmark = [pytest.mark.ts_live, pytest.mark.milestone_m2]


def _http_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=10) as resp:  # nosec B310 - local integration endpoint
        body = resp.read().decode("utf-8")
    parsed = json.loads(body)
    return parsed if isinstance(parsed, dict) else {}


def test_ts_live_002_no_leak_parity(orket_base_url: str) -> None:
    """Placeholder live test: asserts leak-check contract response fields exist and pass."""
    try:
        result = _http_json(
            f"{orket_base_url.rstrip('/')}/textmystery/leak-check",
            {
                "allowed_entities": [
                    "NICK_VALE",
                    "NADIA_BLOOM",
                    "VICTOR_SLATE",
                    "GABE_ROURKE",
                    "PANEL",
                    "CASE",
                    "CAMERA",
                    "11:03",
                ],
                "allowed_fact_values": ["11:03", "PANEL"],
                "text": "That's not something I'm discussing.",
            },
        )
    except (URLError, HTTPError, TimeoutError) as exc:
        pytest.fail(f"Live leak-check endpoint unreachable or failed: {exc}")

    assert "ok" in result
    assert bool(result.get("ok")) is True
    assert result.get("violations") == []
