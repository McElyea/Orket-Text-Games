"""TS-REVEAL-001: Reveal includes culprit chain + refusal causes + facts. Milestone: M1."""

import pytest

from textmystery.engine import reveal, worldgen

pytestmark = [pytest.mark.ts_det, pytest.mark.milestone_m1]


def test_ts_reveal_001_reveal_completeness(default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    result = reveal.compute_reveal(world, accused_npc_id=sample_npc_ids[0])

    assert result.culprit_npc_id == world.culprit_npc_id
    assert result.primary_crime_id == world.primary_crime_id
    assert result.facts
    assert set(result.facts.keys()) == set(world.facts.keys())
    # Each guard-protected fact should be explainable in refusal causes.
    guarded_count = sum(len(v) for v in world.npc_guards.values())
    assert len(result.refusal_causes) == guarded_count
