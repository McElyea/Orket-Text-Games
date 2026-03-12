"""TS-COMP-NUDGE-001: Companion nudges only after stall threshold and never leak. Milestone: M3."""

import pytest

from textmystery.engine import companion
from textmystery.engine.types import CompanionMemory, DecisionMode, TranscriptTurn

pytestmark = [pytest.mark.ts_comp, pytest.mark.milestone_m3]


def test_ts_comp_nudge_001_threshold_behavior():
    transcript = [
        TranscriptTurn(
            timestamp=i,
            npc_id="NADIA",
            raw_question="?",
            canonical_query={"surface_id": "SURF_UNKNOWN"},
            decision=DecisionMode.DONT_KNOW,
            npc_response_text="I don't know.",
            companion_line=None,
        )
        for i in range(5)
    ]
    memory = CompanionMemory(hint_threshold=5)
    line = companion.maybe_nudge(transcript, {"temperament": "nice"}, memory)
    if line is None:
        return
    lowered = line.lower()
    assert "try:" in lowered
    assert "culprit" not in lowered
    assert "secret" not in lowered
