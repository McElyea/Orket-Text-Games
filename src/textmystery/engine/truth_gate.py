from __future__ import annotations

import re
from dataclasses import dataclass

from .types import AnswerDecision, DecisionMode, Fact, WorldGraph


@dataclass(frozen=True)
class GateVerdict:
    """Result of truth gate validation."""

    passed: bool
    reason: str | None = None
    violation_type: str | None = None  # LEAK / CONFESSION / LIE / STYLE


@dataclass(frozen=True)
class GateContext:
    """Everything the truth gate needs to validate a response."""

    world: WorldGraph
    npc_id: str
    decision: AnswerDecision
    candidate_text: str
    max_words: int = 14


class TruthGate:
    """Validates LLM-generated NPC responses against world truth.

    Check order: leak -> confession -> lie -> style.
    First failure short-circuits.
    """

    def validate(self, ctx: GateContext) -> GateVerdict:
        for check in (self._check_leaks, self._check_confession, self._check_lies, self._check_style):
            verdict = check(ctx)
            if not verdict.passed:
                return verdict
        return GateVerdict(passed=True)

    def _check_leaks(self, ctx: GateContext) -> GateVerdict:
        guards = ctx.world.npc_guards.get(ctx.npc_id, set())
        text_upper = ctx.candidate_text.upper()

        for fact_id in guards:
            fact = ctx.world.facts.get(fact_id)
            if fact is None:
                continue
            for fingerprint in _extract_fact_fingerprints(fact):
                if fingerprint.upper() in text_upper:
                    return GateVerdict(
                        passed=False,
                        reason=f"Response reveals guarded information. Avoid mentioning: {fingerprint}",
                        violation_type="LEAK",
                    )

        secret_fact_id = ctx.world.npc_secrets.get(ctx.npc_id)
        if secret_fact_id:
            secret_fact = ctx.world.facts.get(secret_fact_id)
            if secret_fact:
                for fingerprint in _extract_fact_fingerprints(secret_fact):
                    if fingerprint.upper() in text_upper:
                        return GateVerdict(
                            passed=False,
                            reason="Response hints at personal secret. Stay evasive.",
                            violation_type="LEAK",
                        )

        return GateVerdict(passed=True)

    def _check_confession(self, ctx: GateContext) -> GateVerdict:
        if ctx.npc_id != ctx.world.culprit_npc_id:
            return GateVerdict(passed=True)

        text_lower = ctx.candidate_text.lower()
        confession_patterns = [
            r"\bi did it\b",
            r"\bi.m guilty\b",
            r"\bi confess\b",
            r"\bit was me\b",
            r"\bmy fault\b",
            r"\bi.m responsible\b",
            r"\bi took\b.*\baudit drive\b",
            r"\bi moved\b.*\baudit drive\b",
            r"\bi stole\b",
            r"\bi broke in\b",
        ]
        for pattern in confession_patterns:
            if re.search(pattern, text_lower):
                return GateVerdict(
                    passed=False,
                    reason="Response contains self-incrimination. Deny or deflect.",
                    violation_type="CONFESSION",
                )

        return GateVerdict(passed=True)

    def _check_lies(self, ctx: GateContext) -> GateVerdict:
        if ctx.decision.mode != DecisionMode.ANSWER:
            return GateVerdict(passed=True)
        if ctx.decision.fact_id is None:
            return GateVerdict(passed=True)

        fact = ctx.world.facts.get(ctx.decision.fact_id)
        if fact is None:
            return GateVerdict(passed=True)

        payload = fact.value if isinstance(fact.value, dict) else {}
        time_val = payload.get("time") or payload.get("time_code")
        if time_val:
            mentioned_times = re.findall(r"\b\d{1,2}:\d{2}\b", ctx.candidate_text)
            for mentioned in mentioned_times:
                if mentioned not in str(time_val):
                    return GateVerdict(
                        passed=False,
                        reason=f"Response states wrong time. Correct time is {time_val}.",
                        violation_type="LIE",
                    )

        return GateVerdict(passed=True)

    def _check_style(self, ctx: GateContext) -> GateVerdict:
        word_count = len(ctx.candidate_text.split())
        if word_count == 0:
            return GateVerdict(
                passed=False,
                reason="Response is empty. Say something in character.",
                violation_type="STYLE",
            )
        if word_count > ctx.max_words:
            return GateVerdict(
                passed=False,
                reason=f"Response is {word_count} words. Maximum is {ctx.max_words}. Be more terse.",
                violation_type="STYLE",
            )
        return GateVerdict(passed=True)


def _extract_fact_fingerprints(fact: Fact) -> list[str]:
    """Extract string values from a fact that would constitute a leak if mentioned."""
    fingerprints: list[str] = []
    payload = fact.value if isinstance(fact.value, dict) else {}
    if not isinstance(payload, dict):
        return fingerprints
    for key in ("who", "witness", "where", "object", "method", "action", "domain"):
        val = str(payload.get(key, "")).strip()
        if val and len(val) > 2:
            fingerprints.append(val)
            humanized = val.replace("_", " ")
            if humanized != val:
                fingerprints.append(humanized)
    return fingerprints
