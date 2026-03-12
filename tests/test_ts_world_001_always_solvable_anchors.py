"""TS-WORLD-001: Always-solvable anchors. Milestone: M1."""

import pytest

from textmystery.engine import worldgen

pytestmark = [pytest.mark.ts_world, pytest.mark.milestone_m1]


def test_ts_world_001_always_solvable_anchors(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)

    assert world.time_anchors, "Expected at least one time anchor"
    assert world.access_anchors, "Expected at least one access anchor"

    def is_answerable(fact_id: str) -> bool:
        for npc_id in world.selected_npc_ids:
            knowledge = world.npc_knowledge.get(npc_id, set())
            guards = world.npc_guards.get(npc_id, set())
            if fact_id in knowledge and fact_id not in guards:
                return True
        return False

    assert any(is_answerable(fid) for fid in world.time_anchors)
    assert any(is_answerable(fid) for fid in world.access_anchors)
    assert "FACT_PRESENCE_1" in world.facts
    assert "FACT_WITNESS_1" in world.facts

    presence = world.facts["FACT_PRESENCE_1"].value
    witness = world.facts["FACT_WITNESS_1"].value
    assert isinstance(presence, dict) and isinstance(witness, dict)
    assert presence.get("kind") == "presence"
    assert witness.get("kind") == "witness"
    assert presence.get("who")
    assert witness.get("who") == presence.get("who")
    assert witness.get("where") == presence.get("where")


def test_ts_world_001_payload_kinds_and_canonical_ids(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    assert {"SERVICE_DOOR", "BOARDROOM", "ARCHIVE"}.issubset(set(world.access_graph.keys()))

    expected_kinds = {
        "FACT_TIME_ANCHOR_1": "time_anchor",
        "FACT_ACCESS_ANCHOR_1": "access_method",
        "FACT_PRESENCE_1": "presence",
        "FACT_WITNESS_1": "witness",
        "FACT_OBJECT_1": "object",
        "FACT_OBJECT_MOVED_1": "action",
    }
    for fact_id, kind in expected_kinds.items():
        payload = world.facts[fact_id].value
        assert isinstance(payload, dict)
        assert payload.get("kind") == kind
