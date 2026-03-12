"""M1/M2 runtime smoke: ask -> accuse lock -> reveal."""

import pytest

from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_det, pytest.mark.milestone_m1, pytest.mark.milestone_m2]


def test_runtime_accusation_lock_and_reveal(default_config, sample_scene_id, sample_npc_ids):
    world = generate_world(12345, sample_scene_id, sample_npc_ids, "normal", default_config)
    rt = GameRuntime(world=world, settings={"hint_threshold": 3})
    memory = CompanionMemory()

    turn = rt.ask(npc_id=sample_npc_ids[0], raw_question="When were you there?", memory=memory)
    assert "npc_response_text" in turn

    verdict = rt.accuse(accused_npc_id=sample_npc_ids[0])
    assert verdict["outcome"] in {"win", "lose"}
    assert verdict["reveal"].culprit_npc_id == world.culprit_npc_id

    with pytest.raises(RuntimeError):
        rt.ask(npc_id=sample_npc_ids[0], raw_question="one more question", memory=memory)
