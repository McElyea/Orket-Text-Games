from __future__ import annotations

from typing import Any

from .types import AnswerDecision, DecisionMode, IntentId, WorldGraph


def resolve_answer(world: WorldGraph, npc_id: str, canonical_query: dict[str, Any]) -> AnswerDecision:
    """Resolve answer mode using deterministic world graph knowledge and guards."""
    knowledge = world.npc_knowledge.get(npc_id, set())
    guards = world.npc_guards.get(npc_id, set())

    intent_raw = str(canonical_query.get("intent_id") or "").strip()
    if intent_raw == IntentId.WHAT_DO_YOU_KNOW_ABOUT.value:
        # Surface probe path intentionally does not return new fact IDs.
        return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)
    if intent_raw == IntentId.WHO_HAD_ACCESS.value:
        # Access lists are answered from access_graph (people), not method strings.
        place_ref = str(canonical_query.get("place_ref") or "").strip()
        if not place_ref:
            return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)
        if "FACT_ACCESS_ANCHOR_1" in guards:
            return AnswerDecision(mode=DecisionMode.REFUSE, fact_id=None, refusal_reason="guarded")
        if "FACT_ACCESS_ANCHOR_1" in knowledge:
            return AnswerDecision(mode=DecisionMode.ANSWER, fact_id="__ACCESS_LIST__")
        return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)
    if intent_raw == IntentId.DID_YOU_HAVE_ACCESS.value:
        place_ref = str(canonical_query.get("place_ref") or "").strip()
        if not place_ref:
            return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)
        if "FACT_ACCESS_ANCHOR_1" in guards:
            return AnswerDecision(mode=DecisionMode.REFUSE, fact_id=None, refusal_reason="guarded")
        if "FACT_ACCESS_ANCHOR_1" in knowledge:
            return AnswerDecision(mode=DecisionMode.ANSWER, fact_id="__ACCESS_BOOL_YES__")
        return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)

    dynamic = _find_matching_fact(world=world, npc_id=npc_id, canonical_query=canonical_query)
    if dynamic is not None:
        if dynamic in guards:
            return AnswerDecision(mode=DecisionMode.REFUSE, fact_id=None, refusal_reason="guarded")
        return AnswerDecision(mode=DecisionMode.ANSWER, fact_id=dynamic)
    if intent_raw in {IntentId.DID_YOU_SEE.value, IntentId.WHO_WAS_WITH.value}:
        place_ref = _norm(str(canonical_query.get("place_ref") or ""))
        # Witness refusal texture is strongest for service-door line of inquiry.
        # For other places, prefer DONT_KNOW to avoid over-refusal monotony.
        if place_ref and place_ref != "SERVICE_DOOR":
            return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)
        guarded = sorted(guards)
        if guarded:
            return AnswerDecision(mode=DecisionMode.REFUSE, fact_id=None, refusal_reason="guarded")

    fact_id = str(canonical_query.get("fact_id") or "").strip()
    if not fact_id:
        return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)

    if fact_id in guards:
        return AnswerDecision(mode=DecisionMode.REFUSE, fact_id=None, refusal_reason="guarded")
    if fact_id in knowledge:
        return AnswerDecision(mode=DecisionMode.ANSWER, fact_id=fact_id)
    return AnswerDecision(mode=DecisionMode.DONT_KNOW, fact_id=None)


def _find_matching_fact(*, world: WorldGraph, npc_id: str, canonical_query: dict[str, Any]) -> str | None:
    knowledge = world.npc_knowledge.get(npc_id, set())
    guards = world.npc_guards.get(npc_id, set())
    intent_raw = str(canonical_query.get("intent_id") or "").strip()
    if not intent_raw:
        return None
    allowed = _allowed_fact_types(intent_raw)
    if not allowed:
        return None

    guarded_candidate: str | None = None
    for fact_id in sorted(knowledge):
        fact = world.facts.get(fact_id)
        if fact is None:
            continue
        fact_type = str(fact.fact_type or "").strip().lower()
        if fact_type not in allowed:
            continue
        payload = fact.value if isinstance(fact.value, dict) else {}
        if not _payload_matches_query(payload=payload, canonical_query=canonical_query):
            continue
        if fact_id in guards:
            if guarded_candidate is None:
                guarded_candidate = fact_id
            continue
        return fact_id
    return guarded_candidate


def _allowed_fact_types(intent_raw: str) -> set[str]:
    if intent_raw == IntentId.WHEN_WAS.value:
        return {"time"}
    if intent_raw == IntentId.WHERE_WAS.value:
        return {"presence", "location", "linkage"}
    if intent_raw in {IntentId.DID_YOU_SEE.value, IntentId.WHO_WAS_WITH.value}:
        return {"witness", "linkage"}
    if intent_raw == IntentId.DID_YOU_DO.value:
        return {"action"}
    return set()


def _payload_matches_query(*, payload: dict[str, Any], canonical_query: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        payload = {}
    place_ref = _norm(str(canonical_query.get("place_ref") or ""))
    object_id = _norm(str(canonical_query.get("object_id") or ""))
    subject_id = _norm(str(canonical_query.get("subject_id") or ""))
    time_ref = _norm(str(canonical_query.get("time_ref") or ""))

    payload_where = _norm(str(payload.get("where") or ""))
    payload_object = _norm(str(payload.get("object") or ""))
    payload_who = _norm(str(payload.get("who") or ""))
    payload_witness = _norm(str(payload.get("witness") or ""))
    payload_npc = _norm(str(payload.get("npc") or ""))
    payload_when = _norm(str(payload.get("when") or ""))
    payload_time = _norm(str(payload.get("time") or ""))
    payload_time_code = _norm(str(payload.get("time_code") or ""))

    if place_ref and payload_where and payload_where != place_ref:
        return False
    if object_id and payload_object and payload_object != object_id:
        return False
    if subject_id:
        if not any(val == subject_id for val in (payload_who, payload_witness, payload_npc) if val):
            return False
    if time_ref:
        if not any(val == time_ref for val in (payload_when, payload_time, payload_time_code) if val):
            return False
    return True


def _norm(value: str) -> str:
    return str(value or "").strip().upper().replace(" ", "_")
