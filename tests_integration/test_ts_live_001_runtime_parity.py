"""TS-LIVE-001: Runtime parity through Orket integration boundary. Milestone: M2."""

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


def test_ts_live_001_runtime_parity(orket_base_url: str) -> None:
    """Placeholder live test: verifies endpoint reachability and parity contract envelope."""
    try:
        result = _http_json(
            f"{orket_base_url.rstrip('/')}/textmystery/parity-check",
            {
                "run_header": {
                    "seed": 12345,
                    "scene_id": "SCENE_001",
                    "npc_ids": ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
                    "difficulty": "normal",
                    "content_version": "dev",
                    "generator_version": "worldgen_v1",
                },
                "transcript_inputs": [
                    {"turn": 1, "npc_id": "NICK_VALE", "raw_question": "Where were you at 11:03?"},
                    {"turn": 2, "npc_id": "GABE_ROURKE", "raw_question": "Who had access to the panel?"},
                    {"turn": 3, "accuse": {"npc_id": "VICTOR_SLATE"}},
                ],
            },
        )
    except (URLError, HTTPError, TimeoutError) as exc:
        pytest.fail(f"Live parity endpoint unreachable or failed: {exc}")

    assert "world_digest" in result
    assert "turn_results" in result
    assert "accusation_result" in result
