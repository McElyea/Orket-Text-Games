"""TS-LEAK-SURF-001: Surface probe does not yield new fact IDs. Milestone: M2."""

import pytest

from textmystery.engine import classify, resolve, worldgen
from textmystery.engine.types import IntentId

pytestmark = [pytest.mark.ts_leak, pytest.mark.milestone_m2]


def test_ts_leak_surf_001_surface_probe_no_new_fact(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    query = classify.classify_question("What do you know about access?", sample_npc_ids, {})
    assert query.intent_id in {IntentId.WHAT_DO_YOU_KNOW_ABOUT, IntentId.UNCLASSIFIED_AMBIGUOUS}
    decision = resolve.resolve_answer(world, sample_npc_ids[0], {"intent_id": query.intent_id.value})
    assert decision.fact_id is None
