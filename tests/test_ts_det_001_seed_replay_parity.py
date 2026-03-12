"""TS-DET-001: Seed replay parity. Milestone: M1."""

import pytest

from textmystery.engine import worldgen

pytestmark = [pytest.mark.ts_det, pytest.mark.milestone_m1]


def test_ts_det_001_seed_replay_parity(default_config, sample_scene_id, sample_npc_ids):
    seed = 12345
    world_a = worldgen.generate_world(seed, sample_scene_id, sample_npc_ids, "normal", default_config)
    world_b = worldgen.generate_world(seed, sample_scene_id, sample_npc_ids, "normal", default_config)

    assert world_a.digest, "WorldGraph.digest must be populated"
    assert world_a.digest == world_b.digest
