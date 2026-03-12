from __future__ import annotations

import pytest

from textmystery.engine.llm_render import LlmRenderResult, render_via_llm
from textmystery.engine.types import AnswerDecision, CanonicalQuery, DecisionMode, Fact, IntentId, SurfaceId, WorldGraph

try:
    from orket_extension_sdk.llm import GenerateRequest, GenerateResponse, LLMProvider
except ImportError:
    pytest.skip("orket_extension_sdk not available", allow_module_level=True)


def _make_world(culprit: str = "NICK_VALE") -> WorldGraph:
    return WorldGraph(
        scene_template_id="SCENE_001",
        selected_npc_ids=("NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"),
        culprit_npc_id=culprit,
        primary_crime_id="ARCHIVE_BREACH",
        facts={
            "FACT_TIME_ANCHOR_1": Fact("FACT_TIME_ANCHOR_1", "time", {"kind": "time_anchor", "time": "11:03 PM", "time_code": "11:03"}),
            "FACT_PRESENCE_1": Fact("FACT_PRESENCE_1", "presence", {"kind": "presence", "who": "NICK_VALE", "where": "SERVICE_DOOR"}),
        },
        npc_knowledge={"NICK_VALE": {"FACT_TIME_ANCHOR_1"}, "NADIA_BLOOM": set()},
        npc_guards={"NICK_VALE": set(), "NADIA_BLOOM": set()},
        npc_secrets={},
    )


def _query() -> CanonicalQuery:
    return CanonicalQuery(intent_id=IntentId.WHEN_WAS, surface_id=SurfaceId.SURF_TIME, confidence=1.0)


class MockLLMProvider:
    """Mock that returns pre-scripted responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        idx = min(self._call_count, len(self._responses) - 1)
        text = self._responses[idx]
        self._call_count += 1
        return GenerateResponse(text=text, model="mock", latency_ms=10)

    def is_available(self) -> bool:
        return True

    @property
    def call_count(self) -> int:
        return self._call_count


class TestLlmRenderBasic:
    def test_good_response_passes(self):
        provider = MockLLMProvider(["Around 11:03."])
        result = render_via_llm(
            llm_provider=provider,
            world=_make_world(),
            npc_id="NICK_VALE",
            canonical_query=_query(),
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            raw_question="When was it?",
            fact_phrase="At 11:03 PM",
            prompt_config=None,
            turn_index=1,
            template_fallback="At 11:03.",
        )
        assert result.source == "llm"
        assert result.text == "Around 11:03."
        assert result.attempts == 1

    def test_fallback_when_no_provider(self):
        result = render_via_llm(
            llm_provider=None,
            world=_make_world(),
            npc_id="NICK_VALE",
            canonical_query=_query(),
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            raw_question="When was it?",
            fact_phrase="At 11:03 PM",
            prompt_config=None,
            turn_index=1,
            template_fallback="At 11:03.",
        )
        assert result.source == "template_fallback"
        assert result.text == "At 11:03."
        assert result.attempts == 0


class TestLlmRenderRetry:
    def test_retry_on_style_violation(self):
        """First response too long, second passes."""
        provider = MockLLMProvider([
            "Well I think it was around 11:03 PM when the whole thing went down and everything changed for everyone involved",
            "Around 11:03.",
        ])
        result = render_via_llm(
            llm_provider=provider,
            world=_make_world(),
            npc_id="NICK_VALE",
            canonical_query=_query(),
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            raw_question="When was it?",
            fact_phrase="At 11:03 PM",
            prompt_config=None,
            turn_index=1,
            template_fallback="At 11:03.",
        )
        assert result.source == "llm"
        assert result.text == "Around 11:03."
        assert result.attempts == 2

    def test_retry_on_lie(self):
        """First response has wrong time, second is correct."""
        provider = MockLLMProvider(["At 10:45.", "At 11:03."])
        result = render_via_llm(
            llm_provider=provider,
            world=_make_world(),
            npc_id="NICK_VALE",
            canonical_query=_query(),
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            raw_question="When was it?",
            fact_phrase="At 11:03 PM",
            prompt_config=None,
            turn_index=1,
            template_fallback="At 11:03.",
        )
        assert result.source == "llm"
        assert result.text == "At 11:03."
        assert result.attempts == 2


class TestLlmRenderFallback:
    def test_unavailable_provider_fallback(self):
        class UnavailableProvider:
            def generate(self, request):
                return GenerateResponse(text="test", model="mock", latency_ms=0)
            def is_available(self):
                return False

        result = render_via_llm(
            llm_provider=UnavailableProvider(),
            world=_make_world(),
            npc_id="NICK_VALE",
            canonical_query=_query(),
            decision=AnswerDecision(mode=DecisionMode.REFUSE),
            raw_question="Tell me everything.",
            fact_phrase=None,
            prompt_config=None,
            turn_index=1,
            template_fallback="No comment.",
        )
        assert result.source == "template_fallback"
        assert result.text == "No comment."

    def test_refuse_mode_clean_response(self):
        provider = MockLLMProvider(["Not your business."])
        result = render_via_llm(
            llm_provider=provider,
            world=_make_world(),
            npc_id="NICK_VALE",
            canonical_query=_query(),
            decision=AnswerDecision(mode=DecisionMode.REFUSE),
            raw_question="Did you do it?",
            fact_phrase=None,
            prompt_config=None,
            turn_index=1,
            template_fallback="No comment.",
        )
        assert result.source == "llm"
        assert result.text == "Not your business."


class TestLlmRenderConfession:
    def test_culprit_confession_blocked(self):
        """Culprit tries to confess, all attempts blocked, falls back to template."""
        provider = MockLLMProvider(["I did it.", "It was me.", "I confess.", "I'm guilty."])
        result = render_via_llm(
            llm_provider=provider,
            world=_make_world(culprit="NICK_VALE"),
            npc_id="NICK_VALE",
            canonical_query=_query(),
            decision=AnswerDecision(mode=DecisionMode.REFUSE),
            raw_question="Did you do it?",
            fact_phrase=None,
            prompt_config=None,
            turn_index=1,
            template_fallback="No comment.",
            time_budget_ms=5000,
        )
        assert result.text == "No comment."
        assert result.source == "budget_exhausted"
        assert result.attempts >= 4
