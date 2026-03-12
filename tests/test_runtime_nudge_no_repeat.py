"""Companion nudge should avoid exact recent-question repeats when alternatives exist."""

import pytest

from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_comp, pytest.mark.milestone_m3]


def test_runtime_nudge_avoids_recent_repeat(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 1, "nudge_min_gap": 1})
    memory = CompanionMemory(hint_threshold=1)

    # Ask one of the common witness prompts first.
    _ = runtime.ask(
        npc_id="NICK_VALE",
        raw_question="Who did you see near the service door?",
        memory=memory,
    )
    # Trigger another nudge-producing turn.
    turn = runtime.ask(
        npc_id="NICK_VALE",
        raw_question="Who did you see near the service door?",
        memory=memory,
    )
    nudge = str(turn.get("companion_line") or "").lower()
    # Should avoid suggesting the exact same recently asked question as first option.
    assert 'try: "who did you see near the service door?"  then:' not in nudge


def test_runtime_nudge_rotates_when_previous_nudge_repeats(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 1, "nudge_min_gap": 1})
    memory = CompanionMemory(hint_threshold=1)

    first = runtime.ask(
        npc_id="NICK_VALE",
        raw_question="Who did you see near the service door?",
        memory=memory,
    )
    second = runtime.ask(
        npc_id="NICK_VALE",
        raw_question="Who did you see near the service door?",
        memory=memory,
    )
    nudge1 = str(first.get("companion_line") or "").strip()
    nudge2 = str(second.get("companion_line") or "").strip()
    assert nudge1
    assert nudge2
    assert nudge1 != nudge2


def test_runtime_nudge_collision_handles_quotes_and_punctuation(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 1, "nudge_min_gap": 1})
    memory = CompanionMemory(hint_threshold=1)

    _ = runtime.ask(
        npc_id="NICK_VALE",
        raw_question='"Who did you see near the service door?"',
        memory=memory,
    )
    turn = runtime.ask(
        npc_id="NICK_VALE",
        raw_question="who did you see near the service door?",
        memory=memory,
    )
    nudge = str(turn.get("companion_line") or "").lower()
    assert 'try: "who did you see near the service door?"' not in nudge
