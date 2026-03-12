"""Runtime disambiguation flow contract."""

import pytest

from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory, SurfaceId
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def test_runtime_ambiguous_query_returns_disambiguation_marker(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    runtime = GameRuntime(world=world, settings={"hint_threshold": 99})
    turn = runtime.ask(npc_id="NICK_VALE", raw_question="Hey there", memory=CompanionMemory())
    assert turn.get("needs_disambiguation") is True
    assert turn.get("npc_response_text") == ""


def test_runtime_forced_surface_bypasses_disambiguation(default_config):
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
        raw_question="Hey there",
        memory=CompanionMemory(),
        forced_surface=SurfaceId.SURF_TIME,
    )
    assert not turn.get("needs_disambiguation")


def test_runtime_forced_location_maps_to_where_intent(default_config):
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
        raw_question="Hey there",
        memory=CompanionMemory(),
        forced_surface=SurfaceId.SURF_LOCATION,
    )
    assert turn["canonical_query"].intent_id.value == "WHERE_WAS"
