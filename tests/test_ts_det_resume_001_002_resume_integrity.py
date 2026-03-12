"""TS-DET-RESUME-001/002: Resume parity and drift invalidation. Milestone: M1."""

import pytest

from textmystery.engine.persist import validate_resume_header
from textmystery.engine.types import RunHeader

pytestmark = [pytest.mark.ts_det, pytest.mark.milestone_m1]


def test_ts_det_resume_001_parity_validates():
    header = RunHeader(
        seed=42,
        scene_id="SCENE_001",
        npc_ids=("NICK", "NADIA", "VICTOR", "GABE"),
        difficulty="normal",
        content_version="abc",
        generator_version="worldgen_v1",
        world_digest="digest",
    )
    ok, reason = validate_resume_header(
        header=header,
        current_content_version="abc",
        current_generator_version="worldgen_v1",
    )
    assert ok is True
    assert reason is None


def test_ts_det_resume_002_drift_invalidates():
    header = RunHeader(
        seed=42,
        scene_id="SCENE_001",
        npc_ids=("NICK", "NADIA", "VICTOR", "GABE"),
        difficulty="normal",
        content_version="abc",
        generator_version="worldgen_v1",
        world_digest="digest",
    )
    ok, reason = validate_resume_header(
        header=header,
        current_content_version="xyz",
        current_generator_version="worldgen_v1",
    )
    assert ok is False
    assert reason == "content_version_mismatch"
