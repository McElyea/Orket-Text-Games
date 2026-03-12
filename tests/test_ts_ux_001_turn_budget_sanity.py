"""TS-UX-001: Turn budget sanity. Milestone: M3+ (informational until bot exists)."""

import statistics

import pytest

from textmystery.engine import worldgen

pytestmark = [pytest.mark.ts_ux, pytest.mark.milestone_m3]


def _reasonable_interrogator_turn_count(world) -> int:
    # Placeholder deterministic heuristic tied to anchor/search surface.
    anchor_weight = len(world.time_anchors) + len(world.access_anchors) + len(world.linkage_anchors)
    noise_weight = sum(1 for guards in world.npc_guards.values() if guards)
    return max(8, min(25, 8 + anchor_weight + (noise_weight // 2)))


def test_ts_ux_001_turn_budget_sanity(default_config, sample_scene_id, sample_npc_ids):
    counts = []
    for seed in range(100, 120):
        world = worldgen.generate_world(seed, sample_scene_id, sample_npc_ids, "normal", default_config)
        counts.append(_reasonable_interrogator_turn_count(world))

    median = statistics.median(counts)
    p95 = sorted(counts)[int(0.95 * (len(counts) - 1))]

    assert median <= 18
    assert p95 <= 25
