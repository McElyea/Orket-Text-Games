"""TS-TRUTH-002: Culprit inference requires multi-signal triangulation."""

import pytest

from textmystery.engine import worldgen


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def test_ts_truth_002_no_single_answerable_action_reveals_culprit(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)

    answerable_action_facts: set[str] = set()
    for npc_id in world.selected_npc_ids:
        knowledge = world.npc_knowledge.get(npc_id, set())
        guards = world.npc_guards.get(npc_id, set())
        for fact_id in knowledge:
            if fact_id in guards:
                continue
            fact = world.facts.get(fact_id)
            if fact is None:
                continue
            payload = fact.value if isinstance(fact.value, dict) else {}
            if isinstance(payload, dict) and payload.get("kind") == "action":
                answerable_action_facts.add(fact_id)

    # Single-step definitive action facts must stay guarded to preserve triangulation pressure.
    assert "FACT_OBJECT_MOVED_1" not in answerable_action_facts

