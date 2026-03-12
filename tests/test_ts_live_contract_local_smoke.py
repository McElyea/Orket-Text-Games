"""TS-LIVE contract local function smoke tests."""

from __future__ import annotations

import pytest

from textmystery.interfaces.live_contract import leak_check, parity_check


pytestmark = [pytest.mark.ts_live, pytest.mark.milestone_m2]


def test_live_contract_parity_check_shape():
    payload = {
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
            {"turn": 2, "accuse": {"npc_id": "VICTOR_SLATE"}},
        ],
    }
    out = parity_check(payload)
    assert "world_digest" in out
    assert "turn_results" in out
    assert "accusation_result" in out


def test_live_contract_leak_check_shape():
    out = leak_check(
        {
            "allowed_entities": ["NICK_VALE", "NADIA_BLOOM"],
            "allowed_fact_values": ["11:03"],
            "text": "Nadia Bloom was there at 11:03.",
        }
    )
    assert "ok" in out
    assert "violations" in out
