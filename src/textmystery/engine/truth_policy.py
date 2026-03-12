from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from .truth_gate import GateContext, GateVerdict, TruthGate


class TruthPolicyKind(str, Enum):
    ALWAYS_TRUTH = "ALWAYS_TRUTH"
    ALWAYS_LIE = "ALWAYS_LIE"
    HALF_AND_HALF = "HALF_AND_HALF"
    TOPIC_SPLIT = "TOPIC_SPLIT"


@dataclass(frozen=True)
class TruthPolicy:
    """Truth policy assigned to an NPC for a Lie Detector floor."""

    kind: TruthPolicyKind
    seed: int = 0
    truth_topics: tuple[str, ...] = ()
    lie_topics: tuple[str, ...] = ()


def should_be_truthful(
    policy: TruthPolicy,
    question_index: int,
    surface_id: str,
) -> bool:
    """Determine whether a response under this policy should be truthful.

    Pure function. No I/O, no global state, deterministic across runs.
    """
    if policy.kind == TruthPolicyKind.ALWAYS_TRUTH:
        return True
    if policy.kind == TruthPolicyKind.ALWAYS_LIE:
        return False
    if policy.kind == TruthPolicyKind.HALF_AND_HALF:
        material = f"{policy.seed}|{question_index}".encode("utf-8")
        bit = hashlib.sha256(material).digest()[0] & 1
        return bit == 0
    if policy.kind == TruthPolicyKind.TOPIC_SPLIT:
        if surface_id in policy.truth_topics:
            return True
        if surface_id in policy.lie_topics:
            return False
        return True  # default to truth for unspecified topics
    return True


class PolicyGate:
    """Wraps TruthGate with truth policy enforcement.

    For must_lie=False: delegates to TruthGate unchanged.
    For must_lie=True: inverts the lie check (truthful responses are rejected).
    Leak and confession checks always apply regardless of policy.
    """

    def __init__(self) -> None:
        self._truth_gate = TruthGate()

    def validate(self, ctx: GateContext, *, must_lie: bool) -> GateVerdict:
        if not must_lie:
            return self._truth_gate.validate(ctx)

        # Leak check always applies -- NPCs cannot "lie by leaking"
        leak_verdict = self._truth_gate._check_leaks(ctx)
        if not leak_verdict.passed:
            return leak_verdict

        # Confession check always applies
        confession_verdict = self._truth_gate._check_confession(ctx)
        if not confession_verdict.passed:
            return confession_verdict

        # Invert the lie check: if _check_lies passes (truthful), reject
        lie_verdict = self._truth_gate._check_lies(ctx)
        if lie_verdict.passed:
            return GateVerdict(
                passed=False,
                reason="Response is too truthful. Must contain inaccurate information.",
                violation_type="TOO_TRUTHFUL",
            )
        # Response contained a lie -- that's what we want in lie mode

        # Style check always applies
        return self._truth_gate._check_style(ctx)
