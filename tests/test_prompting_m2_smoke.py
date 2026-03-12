"""Prompting smoke tests for archetype packs and deterministic rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from textmystery.engine.prompting import (
    PromptContext,
    load_prompt_config,
    render_text,
    resolve_prompt_pack,
)
from textmystery.engine.render import render_npc_response
from textmystery.engine.types import AnswerDecision, CanonicalQuery, DecisionMode, IntentId, SurfaceId
from textmystery.engine.worldgen import generate_world


pytestmark = [pytest.mark.ts_truth, pytest.mark.milestone_m2]


def test_prompt_pack_load_and_npc_override():
    cfg = load_prompt_config(Path("content"))
    rules, banks = resolve_prompt_pack(cfg, "NICK_VALE")
    assert rules.max_words <= 10
    assert "No comment." in banks.refuse


def test_render_text_is_deterministic_for_same_context():
    cfg = load_prompt_config(Path("content"))
    ctx = PromptContext(
        npc_id="NADIA_BLOOM",
        scene_id="SCENE_001",
        turn_index=2,
        mode="REFUSE",
        topic="access",
    )
    a = render_text(cfg, ctx)
    b = render_text(cfg, ctx)
    assert a == b


def test_render_npc_response_uses_fact_mode_with_prompt_pack(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    canonical = CanonicalQuery(intent_id=IntentId.WHEN_WAS, surface_id=SurfaceId.SURF_TIME, confidence=1.0)
    decision = AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1")
    rendered = render_npc_response(
        world=world,
        npc_id="NICK_VALE",
        canonical_query=canonical,
        decision=decision,
        scene_id=world.scene_template_id,
        turn_index=1,
    )
    assert "11:03" in rendered.text


def test_render_npc_response_varies_fact_phrase_across_turns(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    canonical = CanonicalQuery(intent_id=IntentId.WHEN_WAS, surface_id=SurfaceId.SURF_TIME, confidence=1.0)
    decision = AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1")
    turn1 = render_npc_response(
        world=world,
        npc_id="NICK_VALE",
        canonical_query=canonical,
        decision=decision,
        scene_id=world.scene_template_id,
        turn_index=1,
    )
    turn2 = render_npc_response(
        world=world,
        npc_id="NICK_VALE",
        canonical_query=canonical,
        decision=decision,
        scene_id=world.scene_template_id,
        turn_index=2,
    )
    assert turn1.text != turn2.text


def test_render_linkage_fact_is_humanized(default_config):
    world = generate_world(
        12345,
        "SCENE_001",
        ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"],
        "normal",
        default_config,
    )
    canonical = CanonicalQuery(intent_id=IntentId.DID_YOU_SEE, surface_id=SurfaceId.SURF_WITNESS, confidence=1.0)
    decision = AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_WITNESS_1")
    rendered = render_npc_response(
        world=world,
        npc_id="NICK_VALE",
        canonical_query=canonical,
        decision=decision,
        scene_id=world.scene_template_id,
        turn_index=3,
    )
    lowered = rendered.text.lower()
    assert "present_at" not in lowered
    assert "service" in lowered
