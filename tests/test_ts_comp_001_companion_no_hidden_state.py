"""TS-COMP-001: Companion cannot reference hidden truth. Milestone: M3."""

import pytest

from textmystery.engine import companion
from textmystery.engine.types import CompanionMemory, DecisionMode, TranscriptTurn

pytestmark = [pytest.mark.ts_comp, pytest.mark.milestone_m3]


@pytest.mark.parametrize(
    "transcript",
    [
        [],
        [
            TranscriptTurn(
                timestamp=0,
                npc_id="NADIA",
                raw_question="Who had access?",
                canonical_query={"intent": "access"},
                decision=DecisionMode.REFUSE,
                npc_response_text="I can't share that.",
                companion_line=None,
            )
        ],
    ],
)
def test_ts_comp_001_companion_no_hidden_state(transcript):
    memory = CompanionMemory()
    line = companion.maybe_nudge(transcript, {"temperament": "nice"}, memory)

    if line is None:
        return

    lowered = line.lower()
    forbidden = ["culprit", "guard", "secret"]
    assert all(token not in lowered for token in forbidden)
