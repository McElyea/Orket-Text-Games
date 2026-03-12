"""TS-PERSIST-001: Run artifact save/load roundtrip. Milestone: M1."""

import pytest

from textmystery.engine import persist, worldgen
from textmystery.engine.types import CompanionMemory

pytestmark = [pytest.mark.ts_det, pytest.mark.milestone_m1]


def test_ts_persist_001_run_artifact_roundtrip(tmp_path, default_config, sample_scene_id, sample_npc_ids):
    world = worldgen.generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    artifact = {
        "run_header": {
            "seed": 12345,
            "scene_id": sample_scene_id,
            "npc_ids": sample_npc_ids,
            "difficulty": "normal",
            "world_digest": world.digest,
        },
        "world_graph": world,
        "transcript": [],
        "reveal_graph": {"culprit": world.culprit_npc_id},
    }
    target = tmp_path / "artifacts" / "run.json"
    persist.save_run_artifact(target, artifact)
    loaded = persist.load_run_artifact(target)

    assert loaded["run_header"]["world_digest"] == world.digest
    assert loaded["world_graph"]["culprit_npc_id"] == world.culprit_npc_id


def test_ts_persist_002_companion_memory_roundtrip(tmp_path):
    memory = CompanionMemory(temperament="nice", hint_threshold=4, voice_id="default", sessions_count=2)
    path = tmp_path / "memory.json"
    persist.save_companion_memory(path, memory)
    loaded = persist.load_companion_memory(path)
    assert loaded.temperament == "nice"
    assert loaded.hint_threshold == 4
    assert loaded.sessions_count == 2
