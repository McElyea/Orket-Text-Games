"""Gameplay-kernel readability smoke on a fixed scripted transcript."""

from __future__ import annotations

import pytest

from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def _find_answerable_npc(world, fact_id: str) -> str:
    for npc in world.selected_npc_ids:
        knowledge = world.npc_knowledge.get(npc, set())
        guards = world.npc_guards.get(npc, set())
        if fact_id in knowledge and fact_id not in guards:
            return npc
    return world.selected_npc_ids[0]


def test_gameplay_kernel_smoke_transcript_is_readable(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 99})
    memory = CompanionMemory()

    npc_time = _find_answerable_npc(world, "FACT_TIME_ANCHOR_1")
    npc_presence = _find_answerable_npc(world, "FACT_PRESENCE_1")
    npc_witness = _find_answerable_npc(world, "FACT_WITNESS_1")
    npc_access = _find_answerable_npc(world, "FACT_ACCESS_ANCHOR_1")

    questions = [
        (npc_time, "When were you there?"),
        (npc_presence, "Where were you at 11:03 near the service door?"),
        (npc_access, "Who had access to the service door?"),
        (npc_witness, "Who did you see near the service door?"),
        (world.culprit_npc_id, "Did you move the audit drive?"),
        (npc_access, "What do you know about the boardroom feed?"),
    ]

    outputs: list[str] = []
    for npc_id, question in questions:
        turn = runtime.ask(npc_id=npc_id, raw_question=question, memory=memory)
        text = str(turn["npc_response_text"] or "")
        outputs.append(text)

    joined = "\n".join(outputs).lower()
    assert "fact_" not in joined
    assert "_present_at_" not in joined
    assert ("saw " in joined) or ("seen " in joined) or ("witness" in joined) or ("heard " in joined)
    assert ("i was " in joined) or (" was at the " in joined) or (" by the service door" in joined)
    assert "had access" in joined
