"""TS-CLASS-TIE-001: Deterministic tie-break ordering. Milestone: M1."""

import pytest

from textmystery.engine.classify import classify_question

pytestmark = [pytest.mark.ts_class, pytest.mark.milestone_m1]


def test_ts_class_tie_001_deterministic_tie_break(sample_npc_ids):
    text = "where time"  # intentionally sparse overlap token set
    q1 = classify_question(text, sample_npc_ids, {})
    q2 = classify_question(text, sample_npc_ids, {})
    assert q1.intent_id == q2.intent_id
    assert q1.surface_id == q2.surface_id
