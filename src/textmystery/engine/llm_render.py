from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .npc_prompt import build_npc_prompt
from .truth_gate import GateContext, GateVerdict, TruthGate
from .truth_policy import PolicyGate
from .types import AnswerDecision, CanonicalQuery, WorldGraph


@dataclass(frozen=True)
class LlmRenderResult:
    """Result of LLM-backed NPC response generation."""

    text: str
    source: str  # "llm" | "template_fallback" | "budget_exhausted"
    attempts: int
    total_ms: int
    last_verdict: GateVerdict | None = None


def render_via_llm(
    *,
    llm_provider: Any,
    world: WorldGraph,
    npc_id: str,
    canonical_query: CanonicalQuery,
    decision: AnswerDecision,
    raw_question: str,
    fact_phrase: str | None,
    prompt_config: Any | None,
    turn_index: int,
    template_fallback: str,
    time_budget_ms: int = 2000,
    must_lie: bool = False,
) -> LlmRenderResult:
    """Generate NPC response via LLM with truth gate validation.

    Time-budgeted: retries until budget exhausted, then falls back to template.
    """
    try:
        from orket_extension_sdk.llm import GenerateRequest, LLMProvider
    except ImportError:
        return LlmRenderResult(text=template_fallback, source="template_fallback", attempts=0, total_ms=0)

    if llm_provider is None or not isinstance(llm_provider, LLMProvider):
        return LlmRenderResult(text=template_fallback, source="template_fallback", attempts=0, total_ms=0)
    if not llm_provider.is_available():
        return LlmRenderResult(text=template_fallback, source="template_fallback", attempts=0, total_ms=0)

    gate = PolicyGate()
    start = time.perf_counter()
    attempts = 0
    rejection_reason: str | None = None
    last_verdict: GateVerdict | None = None

    while True:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        remaining_ms = time_budget_ms - elapsed_ms
        if remaining_ms <= 100:
            break

        prompt_pack = build_npc_prompt(
            world=world,
            npc_id=npc_id,
            canonical_query=canonical_query,
            decision=decision,
            raw_question=raw_question,
            fact_phrase=fact_phrase,
            prompt_config=prompt_config,
            turn_index=turn_index,
            rejection_reason=rejection_reason,
            must_lie=must_lie,
        )

        try:
            request = GenerateRequest(
                system_prompt=prompt_pack.system_prompt,
                user_message=prompt_pack.user_message,
                max_tokens=64,
                temperature=0.7,
                stop_sequences=["\n"],
            )
            response = llm_provider.generate(request)
            candidate = response.text.strip().strip('"').strip("'")
        except Exception:
            break

        attempts += 1
        if not candidate:
            rejection_reason = "Empty response."
            continue

        gate_ctx = GateContext(
            world=world,
            npc_id=npc_id,
            decision=decision,
            candidate_text=candidate,
            max_words=prompt_pack.max_words,
        )
        verdict = gate.validate(gate_ctx, must_lie=must_lie)
        last_verdict = verdict

        if verdict.passed:
            total_ms = int((time.perf_counter() - start) * 1000)
            return LlmRenderResult(
                text=candidate,
                source="llm",
                attempts=attempts,
                total_ms=total_ms,
                last_verdict=verdict,
            )

        rejection_reason = verdict.reason

    total_ms = int((time.perf_counter() - start) * 1000)
    return LlmRenderResult(
        text=template_fallback,
        source="budget_exhausted" if attempts > 0 else "template_fallback",
        attempts=attempts,
        total_ms=total_ms,
        last_verdict=last_verdict,
    )
