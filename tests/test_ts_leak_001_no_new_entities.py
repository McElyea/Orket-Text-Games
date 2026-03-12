"""TS-LEAK-001: NPC response has no new named entities. Milestone: M2/M4."""

import re

import pytest

from textmystery.engine import resolve, worldgen

pytestmark = [pytest.mark.ts_leak, pytest.mark.milestone_m2, pytest.mark.milestone_m4]


def test_ts_leak_001_no_new_entities(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)

    allowlist = set(sample_npc_ids)
    allowlist.update(world.access_graph.keys())

    target_npc = sample_npc_ids[0]
    decision = resolve.resolve_answer(world, target_npc, {"fact_id": next(iter(world.facts.keys()))})

    response_text = str(getattr(decision, "response_text", ""))
    entities = set(re.findall(r"\b[A-Z][a-zA-Z0-9_]+\b", response_text))
    unauthorized = entities - allowlist
    assert not unauthorized, f"Unauthorized entities found: {sorted(unauthorized)}"
