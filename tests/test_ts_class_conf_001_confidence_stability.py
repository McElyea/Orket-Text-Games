"""TS-CLASS-CONF-001: Confidence is stable and classifier-only. Milestone: M1."""

import pytest

from textmystery.engine.classify import classify_question

pytestmark = [pytest.mark.ts_class, pytest.mark.milestone_m1]


def test_ts_class_conf_001_stable_confidence(sample_npc_ids):
    text = "Who had access to the vault keycard?"
    q1 = classify_question(text, sample_npc_ids, {"world": "ignored"})
    q2 = classify_question(text, sample_npc_ids, {"world": "different"})
    assert 0.0 <= q1.confidence <= 1.0
    assert q1.confidence == q2.confidence
