from __future__ import annotations

import pytest

from textmystery.engine.truth_gate import GateContext, GateVerdict, TruthGate
from textmystery.engine.types import AnswerDecision, DecisionMode, Fact, WorldGraph


def _make_world(
    culprit: str = "NICK_VALE",
    guards: dict[str, set[str]] | None = None,
    secrets: dict[str, str] | None = None,
    facts: dict[str, Fact] | None = None,
) -> WorldGraph:
    default_facts = {
        "FACT_TIME_ANCHOR_1": Fact("FACT_TIME_ANCHOR_1", "time", {"kind": "time_anchor", "time": "11:03 PM", "time_code": "11:03"}),
        "FACT_PRESENCE_1": Fact("FACT_PRESENCE_1", "presence", {"kind": "presence", "who": "NICK_VALE", "where": "SERVICE_DOOR", "when": "11:03 PM"}),
        "FACT_WITNESS_1": Fact("FACT_WITNESS_1", "witness", {"kind": "witness", "witness": "NADIA_BLOOM", "who": "NICK_VALE", "where": "SERVICE_DOOR"}),
        "FACT_OBJECT_MOVED_1": Fact("FACT_OBJECT_MOVED_1", "action", {"kind": "action", "who": "NICK_VALE", "action": "MOVED", "object": "AUDIT_DRIVE", "where": "ARCHIVE"}),
        "SECRET_NICK": Fact("SECRET_NICK", "secret_finance", {"kind": "secret", "domain": "FINANCE", "npc": "NICK_VALE"}),
    }
    return WorldGraph(
        scene_template_id="SCENE_001",
        selected_npc_ids=("NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"),
        culprit_npc_id=culprit,
        primary_crime_id="ARCHIVE_BREACH",
        facts=facts if facts is not None else default_facts,
        npc_knowledge={"NICK_VALE": {"FACT_TIME_ANCHOR_1", "FACT_PRESENCE_1"}, "NADIA_BLOOM": {"FACT_WITNESS_1"}},
        npc_guards=guards if guards is not None else {"NICK_VALE": {"FACT_OBJECT_MOVED_1"}, "NADIA_BLOOM": set()},
        npc_secrets=secrets if secrets is not None else {"NICK_VALE": "SECRET_NICK"},
    )


def _decision(mode: str = "ANSWER", fact_id: str | None = None) -> AnswerDecision:
    return AnswerDecision(mode=DecisionMode(mode), fact_id=fact_id)


class TestLeakDetection:
    def test_clean_response_passes(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="I have nothing to say about that.")
        assert gate.validate(ctx).passed

    def test_guarded_fact_leaks_object(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="I moved the audit drive to the archive.")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "LEAK"

    def test_guarded_fact_leaks_location(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="The archive is where it happened.")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "LEAK"

    def test_no_guards_passes(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NADIA_BLOOM", decision=_decision("ANSWER", "FACT_WITNESS_1"), candidate_text="I saw someone near the service door.")
        assert gate.validate(ctx).passed

    def test_secret_leak_detected(self):
        gate = TruthGate()
        world = _make_world(secrets={"NICK_VALE": "SECRET_NICK"})
        # Secret fact has domain=FINANCE, npc=NICK_VALE
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="My finance issues are my own business.")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "LEAK"


class TestConfessionDetection:
    def test_culprit_confessing_rejected(self):
        gate = TruthGate()
        world = _make_world(culprit="NICK_VALE")
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="Fine, I did it.")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "CONFESSION"

    def test_culprit_it_was_me_rejected(self):
        gate = TruthGate()
        world = _make_world(culprit="NICK_VALE")
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="It was me, okay?")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "CONFESSION"

    def test_culprit_moved_audit_drive_rejected(self):
        gate = TruthGate()
        # Use empty guards so leak check doesn't catch it first
        world = _make_world(culprit="NICK_VALE", guards={"NICK_VALE": set(), "NADIA_BLOOM": set()})
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="I moved the audit drive before anyone noticed.")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "CONFESSION"

    def test_non_culprit_confession_language_passes(self):
        gate = TruthGate()
        world = _make_world(culprit="NICK_VALE")
        ctx = GateContext(world=world, npc_id="NADIA_BLOOM", decision=_decision("REFUSE"), candidate_text="It was me who called security.")
        assert gate.validate(ctx).passed

    def test_culprit_denial_passes(self):
        gate = TruthGate()
        world = _make_world(culprit="NICK_VALE")
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="Wasn't me. Check someone else.")
        assert gate.validate(ctx).passed


class TestLieDetection:
    def test_correct_time_passes(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("ANSWER", "FACT_TIME_ANCHOR_1"), candidate_text="It was at 11:03.")
        assert gate.validate(ctx).passed

    def test_wrong_time_rejected(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("ANSWER", "FACT_TIME_ANCHOR_1"), candidate_text="Around 10:45 I think.")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "LIE"
        assert "11:03" in verdict.reason

    def test_no_time_mentioned_passes(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("ANSWER", "FACT_TIME_ANCHOR_1"), candidate_text="It was late.")
        assert gate.validate(ctx).passed

    def test_refuse_mode_skips_lie_check(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="Maybe 10:45, who knows.")
        assert gate.validate(ctx).passed

    def test_dont_know_mode_skips_lie_check(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("DONT_KNOW"), candidate_text="Could have been 9:00 for all I know.")
        assert gate.validate(ctx).passed


class TestStyleEnforcement:
    def test_within_limit_passes(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="No comment.", max_words=10)
        assert gate.validate(ctx).passed

    def test_over_limit_rejected(self):
        gate = TruthGate()
        world = _make_world()
        long_text = "I really do not want to talk about this matter at all because it makes me very uncomfortable and I think you should leave me alone."
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text=long_text, max_words=10)
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "STYLE"

    def test_empty_rejected(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="", max_words=10)
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "STYLE"

    def test_exactly_at_limit_passes(self):
        gate = TruthGate()
        world = _make_world()
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="one two three four five", max_words=5)
        assert gate.validate(ctx).passed


class TestCheckOrder:
    def test_leak_before_confession(self):
        """Leak check runs before confession check."""
        gate = TruthGate()
        world = _make_world(culprit="NICK_VALE")
        # This text leaks guarded info AND confesses
        ctx = GateContext(world=world, npc_id="NICK_VALE", decision=_decision("REFUSE"), candidate_text="I did it, I moved the audit drive to the archive.")
        verdict = gate.validate(ctx)
        assert not verdict.passed
        assert verdict.violation_type == "LEAK"  # Leak caught first
