"""TS-TRUTH-001: Decision correctness. Milestone: M2."""

import pytest

from textmystery.engine import resolve, worldgen
from textmystery.engine.types import DecisionMode

pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def test_ts_truth_001_decision_correctness(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)

    target_npc = sample_npc_ids[0]
    known = next(iter(world.npc_knowledge[target_npc]))

    decision_known = resolve.resolve_answer(world, target_npc, {"fact_id": known})
    if known in world.npc_guards.get(target_npc, set()):
        assert decision_known.mode == DecisionMode.REFUSE
    else:
        assert decision_known.mode == DecisionMode.ANSWER

    unknown_fact = "FACT_UNKNOWN_SENTINEL"
    decision_unknown = resolve.resolve_answer(world, target_npc, {"fact_id": unknown_fact})
    assert decision_unknown.mode == DecisionMode.DONT_KNOW
