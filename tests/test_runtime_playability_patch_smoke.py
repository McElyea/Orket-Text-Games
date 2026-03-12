"""Playability patch smoke: angle forcing, access list answers, and identity handling."""

from __future__ import annotations

import pytest

from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory, SurfaceId
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def test_access_question_returns_people_list(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 99})
    turn = runtime.ask(
        npc_id="NADIA_BLOOM",
        raw_question="Who had access to the service door?",
        memory=CompanionMemory(),
        forced_surface=SurfaceId.SURF_ACCESS,
    )
    text = turn["npc_response_text"].lower()
    assert "had access" in text
    assert "service_door_keycard" not in text


def test_identity_question_is_answered(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 99})
    turn = runtime.ask(
        npc_id="NICK_VALE",
        raw_question="What's your name?",
        memory=CompanionMemory(),
    )
    assert turn["npc_response_text"] == "Nick Vale"


def test_discovery_keys_are_namespaced_and_stable(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 99})
    target_npc = world.culprit_npc_id
    _ = runtime.ask(
        npc_id=target_npc,
        raw_question="Where were you at 11:03 near the service door?",
        memory=CompanionMemory(),
    )
    assert any(item.startswith("disc:fact:") for item in runtime.discoveries)
    assert any(item.startswith("disc:place:") for item in runtime.discoveries)
    assert any(item.startswith("disc:npc:") for item in runtime.discoveries)
