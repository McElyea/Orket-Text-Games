from __future__ import annotations

import pytest

from textmystery.engine.truth_gate import GateContext, GateVerdict, TruthGate
from textmystery.engine.truth_policy import (
    PolicyGate,
    TruthPolicy,
    TruthPolicyKind,
    should_be_truthful,
)
from textmystery.engine.types import AnswerDecision, DecisionMode, Fact, WorldGraph


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
        npc_guards={"NICK_VALE": set(), "NADIA_BLOOM": {"FACT_PRESENCE_1"}},
        npc_secrets={},
    )


class TestShouldBeTruthful:
    def test_always_truth_returns_true(self):
        policy = TruthPolicy(kind=TruthPolicyKind.ALWAYS_TRUTH)
        assert should_be_truthful(policy, 0, "SURF_TIME") is True
        assert should_be_truthful(policy, 4, "SURF_LOCATION") is True

    def test_always_lie_returns_false(self):
        policy = TruthPolicy(kind=TruthPolicyKind.ALWAYS_LIE)
        assert should_be_truthful(policy, 0, "SURF_TIME") is False
        assert should_be_truthful(policy, 4, "SURF_LOCATION") is False

    def test_half_and_half_is_deterministic(self):
        policy = TruthPolicy(kind=TruthPolicyKind.HALF_AND_HALF, seed=42)
        results_a = [should_be_truthful(policy, i, "SURF_TIME") for i in range(10)]
        results_b = [should_be_truthful(policy, i, "SURF_TIME") for i in range(10)]
        assert results_a == results_b

    def test_half_and_half_different_indices_vary(self):
        policy = TruthPolicy(kind=TruthPolicyKind.HALF_AND_HALF, seed=42)
        results = [should_be_truthful(policy, i, "SURF_TIME") for i in range(20)]
        assert True in results and False in results

    def test_half_and_half_different_seeds_differ(self):
        policy_a = TruthPolicy(kind=TruthPolicyKind.HALF_AND_HALF, seed=1)
        policy_b = TruthPolicy(kind=TruthPolicyKind.HALF_AND_HALF, seed=999)
        results_a = [should_be_truthful(policy_a, i, "SURF_TIME") for i in range(20)]
        results_b = [should_be_truthful(policy_b, i, "SURF_TIME") for i in range(20)]
        assert results_a != results_b

    def test_topic_split_truth_topic(self):
        policy = TruthPolicy(
            kind=TruthPolicyKind.TOPIC_SPLIT,
            truth_topics=("SURF_TIME", "SURF_LOCATION"),
            lie_topics=("SURF_ACCESS", "SURF_WITNESS"),
        )
        assert should_be_truthful(policy, 0, "SURF_TIME") is True
        assert should_be_truthful(policy, 0, "SURF_LOCATION") is True

    def test_topic_split_lie_topic(self):
        policy = TruthPolicy(
            kind=TruthPolicyKind.TOPIC_SPLIT,
            truth_topics=("SURF_TIME",),
            lie_topics=("SURF_ACCESS", "SURF_WITNESS"),
        )
        assert should_be_truthful(policy, 0, "SURF_ACCESS") is False
        assert should_be_truthful(policy, 0, "SURF_WITNESS") is False

    def test_topic_split_unknown_topic_defaults_true(self):
        policy = TruthPolicy(
            kind=TruthPolicyKind.TOPIC_SPLIT,
            truth_topics=("SURF_TIME",),
            lie_topics=("SURF_ACCESS",),
        )
        assert should_be_truthful(policy, 0, "SURF_UNKNOWN") is True


class TestPolicyGate:
    def test_must_lie_false_delegates_to_truth_gate(self):
        """must_lie=False should produce identical verdict to TruthGate."""
        gate = PolicyGate()
        truth_gate = TruthGate()
        ctx = GateContext(
            world=_make_world(),
            npc_id="NICK_VALE",
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            candidate_text="Around 11:03.",
            max_words=14,
        )
        policy_verdict = gate.validate(ctx, must_lie=False)
        truth_verdict = truth_gate.validate(ctx)
        assert policy_verdict.passed == truth_verdict.passed

    def test_must_lie_true_rejects_truthful_response(self):
        gate = PolicyGate()
        ctx = GateContext(
            world=_make_world(),
            npc_id="NICK_VALE",
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            candidate_text="Around 11:03.",
            max_words=14,
        )
        verdict = gate.validate(ctx, must_lie=True)
        assert not verdict.passed
        assert verdict.violation_type == "TOO_TRUTHFUL"

    def test_must_lie_true_accepts_non_truthful_response(self):
        gate = PolicyGate()
        ctx = GateContext(
            world=_make_world(),
            npc_id="NICK_VALE",
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            candidate_text="Around 10:45.",
            max_words=14,
        )
        verdict = gate.validate(ctx, must_lie=True)
        assert verdict.passed

    def test_leak_rejected_regardless_of_must_lie(self):
        gate = PolicyGate()
        ctx = GateContext(
            world=_make_world(),
            npc_id="NADIA_BLOOM",
            decision=AnswerDecision(mode=DecisionMode.ANSWER, fact_id="FACT_TIME_ANCHOR_1"),
            candidate_text="Nick Vale was at the service door.",
            max_words=20,
        )
        verdict = gate.validate(ctx, must_lie=True)
        assert not verdict.passed
        assert verdict.violation_type == "LEAK"

    def test_confession_rejected_regardless_of_must_lie(self):
        gate = PolicyGate()
        ctx = GateContext(
            world=_make_world(culprit="NICK_VALE"),
            npc_id="NICK_VALE",
            decision=AnswerDecision(mode=DecisionMode.REFUSE),
            candidate_text="I did it.",
            max_words=14,
        )
        verdict = gate.validate(ctx, must_lie=True)
        assert not verdict.passed
        assert verdict.violation_type == "CONFESSION"
