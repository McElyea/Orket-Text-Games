"""Witness answers should keep nudges on corroboration chain."""

import pytest

from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_comp, pytest.mark.milestone_m3]


def test_witness_answer_prefers_chain_nudges(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    witness_npc = ""
    payload = world.facts.get("FACT_WITNESS_1").value if world.facts.get("FACT_WITNESS_1") else {}
    if isinstance(payload, dict):
        witness_npc = str(payload.get("witness", "")).strip()
    witness_npc = witness_npc or world.selected_npc_ids[0]

    runtime = GameRuntime(world=world, settings={"hint_threshold": 1, "nudge_min_gap": 1})
    _ = runtime.ask(
        npc_id=world.culprit_npc_id,
        raw_question="Who did you see near the boardroom?",
        memory=CompanionMemory(hint_threshold=1),
    )
    turn = runtime.ask(
        npc_id=witness_npc,
        raw_question="Who did you see near the service door?",
        memory=CompanionMemory(hint_threshold=1),
    )
    nudge = str(turn.get("companion_line") or "").lower()
    if turn["decision"].mode.value != "ANSWER":
        pytest.skip("witness turn was not answerable for this deterministic world setup")
    assert nudge
    assert "audit drive" not in nudge
    assert ("confirm" in nudge) or ("where were you" in nudge) or ("who had access" in nudge)
