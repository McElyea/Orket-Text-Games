"""Intent-scoped refusal rendering should avoid generic action-tone phrases."""

import pytest

from textmystery.engine.render import render_npc_response
from textmystery.engine.types import AnswerDecision, CanonicalQuery, DecisionMode, IntentId, SurfaceId
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m3]


def test_witness_refuse_style_is_intent_scoped(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    canonical = CanonicalQuery(intent_id=IntentId.DID_YOU_SEE, surface_id=SurfaceId.SURF_WITNESS, confidence=1.0)
    rendered = render_npc_response(
        world=world,
        npc_id="NICK_VALE",
        canonical_query=canonical,
        decision=AnswerDecision(mode=DecisionMode.REFUSE, fact_id=None, refusal_reason="guarded"),
        scene_id="SCENE_001",
        turn_index=1,
    )
    text = rendered.text.lower()
    assert "cute question" not in text
    assert text in {
        "not talking about who i saw.",
        "i can't confirm who was there.",
        "i won't name names.",
        "not discussing witnesses.",
    }


def test_relationship_refuse_style_is_not_action_tone(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    canonical = CanonicalQuery(intent_id=IntentId.WHO_WAS_WITH, surface_id=SurfaceId.SURF_RELATIONSHIP, confidence=1.0)
    rendered = render_npc_response(
        world=world,
        npc_id="VICTOR_SLATE",
        canonical_query=canonical,
        decision=AnswerDecision(mode=DecisionMode.REFUSE, fact_id=None, refusal_reason="guarded"),
        scene_id="SCENE_001",
        turn_index=1,
    )
    text = rendered.text.lower()
    assert text != "no."
    assert "cute question" not in text

