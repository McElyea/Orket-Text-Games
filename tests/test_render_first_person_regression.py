"""First-person render regression checks for speaker-owned facts."""

import pytest

from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def test_first_person_presence_for_speaker_owned_fact(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 99})
    turn = runtime.ask(
        npc_id=world.culprit_npc_id,
        raw_question="Where were you at 11:03 near the service door?",
        memory=CompanionMemory(),
    )
    text = str(turn["npc_response_text"] or "").strip().lower()
    assert text.startswith("i ") or " i was " in f" {text}"


def test_first_person_witness_for_speaker_owned_fact(default_config):
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

    runtime = GameRuntime(world=world, settings={"hint_threshold": 99})
    turn = runtime.ask(
        npc_id=witness_npc,
        raw_question="Who did you see near the service door?",
        memory=CompanionMemory(),
    )
    text = str(turn["npc_response_text"] or "").strip().lower()
    if turn["decision"].mode.value == "ANSWER":
        assert text.startswith("i ") or " i saw " in f" {text}" or " i placed " in f" {text}"

