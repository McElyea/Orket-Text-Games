"""TS-TRUTH-003: Resolver dynamic matching before static fallback."""

import pytest

from textmystery.engine import resolve, worldgen
from textmystery.engine.types import DecisionMode


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def _find_npc_with_fact(world, fact_id: str) -> str:
    for npc in world.selected_npc_ids:
        if fact_id in world.npc_knowledge.get(npc, set()):
            return npc
    return world.selected_npc_ids[0]


def test_resolver_dynamic_match_answers_when_static_fact_id_is_wrong(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    npc = world.culprit_npc_id
    decision = resolve.resolve_answer(
        world,
        npc,
        {
            "intent_id": "WHERE_WAS",
            "fact_id": "FACT_NOT_REAL",
            "place_ref": "SERVICE_DOOR",
        },
    )
    assert decision.mode == DecisionMode.ANSWER
    assert decision.fact_id == "FACT_PRESENCE_1"


def test_resolver_dynamic_match_deterministic_choice(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    npc = _find_npc_with_fact(world, "FACT_WITNESS_1")
    payload = {
        "intent_id": "DID_YOU_SEE",
        "fact_id": "FACT_UNKNOWN",
        "place_ref": "SERVICE_DOOR",
    }
    a = resolve.resolve_answer(world, npc, payload)
    b = resolve.resolve_answer(world, npc, payload)
    assert a.mode == b.mode
    assert a.fact_id == b.fact_id


def test_resolver_dynamic_match_returns_refuse_for_guarded_action(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    npc = world.culprit_npc_id
    decision = resolve.resolve_answer(
        world,
        npc,
        {
            "intent_id": "DID_YOU_DO",
            "object_id": "AUDIT_DRIVE",
        },
    )
    assert decision.mode == DecisionMode.REFUSE


def test_resolver_witness_intent_prefers_witness_kind_not_presence(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    witness_payload = world.facts["FACT_WITNESS_1"].value if "FACT_WITNESS_1" in world.facts else {}
    witness_npc = str(witness_payload.get("witness", "")) if isinstance(witness_payload, dict) else ""
    if not witness_npc:
        witness_npc = world.selected_npc_ids[0]
    decision = resolve.resolve_answer(
        world,
        witness_npc,
        {
            "intent_id": "DID_YOU_SEE",
            "place_ref": "SERVICE_DOOR",
            "fact_id": "FACT_PRESENCE_1",  # stale static fallback should be ignored by dynamic-first matching
        },
    )
    assert decision.mode == DecisionMode.ANSWER
    assert decision.fact_id == "FACT_WITNESS_1"


def test_resolver_witness_intent_without_match_uses_refuse_when_guarded(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    npc = world.culprit_npc_id
    decision = resolve.resolve_answer(
        world,
        npc,
        {
            "intent_id": "DID_YOU_SEE",
            "place_ref": "SERVICE_DOOR",
            "subject_id": "SOMEONE_ELSE",
            "fact_id": "FACT_WITNESS_1",
        },
    )
    assert decision.mode == DecisionMode.REFUSE
    assert decision.refusal_reason == "guarded"


def test_resolver_witness_intent_non_service_place_prefers_dont_know(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    npc = world.culprit_npc_id
    decision = resolve.resolve_answer(
        world,
        npc,
        {
            "intent_id": "DID_YOU_SEE",
            "place_ref": "BOARDROOM",
        },
    )
    assert decision.mode == DecisionMode.DONT_KNOW
