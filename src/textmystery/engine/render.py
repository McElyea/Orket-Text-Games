from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import re
from typing import Any

import yaml

from .prompting import PromptConfig, PromptContext, PromptingError, load_prompt_config, render_text
from .types import AnswerDecision, AudioHint, CanonicalQuery, DecisionMode, IntentId, WorldGraph


@dataclass(frozen=True)
class RenderedResponse:
    text: str
    audio_hint: AudioHint | None = None


_REFUSE_STYLE = {"NICK": "No comment.", "NADIA": "I can't share that.", "VICTOR": "...", "GABE": "Next."}
_DONT_KNOW_STYLE = {"NICK": "I don't know.", "NADIA": "I wasn't told.", "VICTOR": "No idea.", "GABE": "Not my area."}

_REFUSE_BY_INTENT: dict[str, dict[str, str]] = {
    "witness": {
        "NICK": "Not talking about who I saw.",
        "NADIA": "I can't confirm who was there.",
        "VICTOR": "I won't name names.",
        "GABE": "Not discussing witnesses.",
    },
    "access": {
        "NICK": "I won't discuss access routes.",
        "NADIA": "Access records are not for me to share.",
        "VICTOR": "No access comment.",
        "GABE": "Access stays sealed.",
    },
    "action": {
        "NICK": "No comment on that action.",
        "NADIA": "I can't answer that action line.",
        "VICTOR": "Not answering that.",
        "GABE": "Next question.",
    },
}

_DONT_KNOW_BY_INTENT: dict[str, dict[str, str]] = {
    "witness": {
        "NICK": "Didn't clock anyone I can prove.",
        "NADIA": "I can't place anyone there.",
        "VICTOR": "Didn't clock anyone.",
        "GABE": "No witness I can name.",
    },
    "access": {
        "NICK": "I don't know who had that route.",
        "NADIA": "I wasn't given that access map.",
        "VICTOR": "No access read on that.",
        "GABE": "No access intel on that.",
    },
}


_SURFACE_TOPIC: dict[str, str] = {
    "SURF_TIME": "timing",
    "SURF_ACCESS": "access",
    "SURF_LOCATION": "locations",
    "SURF_WITNESS": "who was seen",
    "SURF_OBJECT": "objects",
    "SURF_RELATIONSHIP": "relationships",
    "SURF_MOTIVE": "motives",
    "SURF_ALIBI": "alibis",
    "SURF_META": "the case",
    "SURF_UNKNOWN": "the case",
}


def _persona_key(npc_id: str) -> str:
    return str(npc_id or "").strip().upper().split("_")[0]


def render_npc_response(
    *,
    world: WorldGraph,
    npc_id: str,
    canonical_query: CanonicalQuery,
    decision: AnswerDecision,
    scene_id: str | None = None,
    turn_index: int = 0,
) -> RenderedResponse:
    text_response = _render_npc_text(
        world=world,
        npc_id=npc_id,
        canonical_query=canonical_query,
        decision=decision,
        scene_id=scene_id,
        turn_index=turn_index,
    )
    audio_hint = _build_audio_hint(npc_id, decision.mode)
    return RenderedResponse(text=text_response.text, audio_hint=audio_hint)


def _render_npc_text(
    *,
    world: WorldGraph,
    npc_id: str,
    canonical_query: CanonicalQuery,
    decision: AnswerDecision,
    scene_id: str | None = None,
    turn_index: int = 0,
) -> RenderedResponse:
    key = _persona_key(npc_id)
    scene = str(scene_id or world.scene_template_id or "SCENE_001")
    topic = _SURFACE_TOPIC.get(canonical_query.surface_id.value, "the case")
    cfg = _prompt_cfg()

    if canonical_query.intent_id == IntentId.UNCLASSIFIED_AMBIGUOUS:
        return RenderedResponse(
            text=_render_or_fallback(
                cfg=cfg,
                fallback="Be specific. Ask about time, access, or who saw who.",
                ctx=PromptContext(
                    npc_id=npc_id,
                    scene_id=scene,
                    turn_index=turn_index,
                    mode="CLARIFY",
                    topic=topic,
                ),
            )
        )

    if canonical_query.intent_id.value == "WHAT_DO_YOU_KNOW_ABOUT":
        if canonical_query.surface_id.value == "SURF_UNKNOWN":
            return RenderedResponse(
                text=_render_or_fallback(
                    cfg=cfg,
                    fallback="Be specific.",
                    ctx=PromptContext(
                        npc_id=npc_id,
                        scene_id=scene,
                        turn_index=turn_index,
                        mode="CLARIFY",
                        topic=topic,
                    ),
                )
            )
        return RenderedResponse(
            text=_render_or_fallback(
                cfg=cfg,
                fallback="Ask me about time or access.",
                ctx=PromptContext(
                    npc_id=npc_id,
                    scene_id=scene,
                    turn_index=turn_index,
                    mode="NUDGE",
                    topic=topic,
                ),
            )
        )

    if decision.mode == DecisionMode.REFUSE:
        if canonical_query.intent_id == IntentId.WHO_HAD_ACCESS and not canonical_query.place_ref:
            return RenderedResponse(text=_clarify_for_intent(IntentId.WHO_HAD_ACCESS))
        if canonical_query.intent_id == IntentId.DID_YOU_HAVE_ACCESS and not canonical_query.place_ref:
            return RenderedResponse(text=_clarify_for_intent(IntentId.DID_YOU_HAVE_ACCESS))
        return RenderedResponse(
            text=_render_or_fallback(
                cfg=cfg,
                fallback=_refuse_text(intent_id=canonical_query.intent_id, persona_key=key),
                ctx=PromptContext(
                    npc_id=npc_id,
                    scene_id=scene,
                    turn_index=turn_index,
                    mode="REFUSE",
                    topic=topic,
                ),
            )
        )

    if decision.mode == DecisionMode.DONT_KNOW:
        if canonical_query.intent_id == IntentId.WHO_HAD_ACCESS and not canonical_query.place_ref:
            return RenderedResponse(text=_clarify_for_intent(IntentId.WHO_HAD_ACCESS))
        if canonical_query.intent_id == IntentId.DID_YOU_HAVE_ACCESS and not canonical_query.place_ref:
            return RenderedResponse(text=_clarify_for_intent(IntentId.DID_YOU_HAVE_ACCESS))
        return RenderedResponse(
            text=_render_or_fallback(
                cfg=cfg,
                fallback=_dont_know_text(intent_id=canonical_query.intent_id, persona_key=key),
                ctx=PromptContext(
                    npc_id=npc_id,
                    scene_id=scene,
                    turn_index=turn_index,
                    mode="DONT_KNOW",
                    topic=topic,
                ),
            )
        )

    if decision.fact_id == "__ACCESS_LIST__":
        if not canonical_query.place_ref:
            return RenderedResponse(text=_clarify_for_intent(IntentId.WHO_HAD_ACCESS))
        people = _people_with_access(world, canonical_query.place_ref)
        if not people:
            return RenderedResponse(text="I don't know who had access.")
        if len(people) == 1:
            fact_phrase = f"{people[0]} had access"
        else:
            fact_phrase = f"{', '.join(people[:-1])}, and {people[-1]} had access"
        return RenderedResponse(
            text=_render_or_fallback(
                cfg=cfg,
                fallback=fact_phrase + ".",
                ctx=PromptContext(
                    npc_id=npc_id,
                    scene_id=scene,
                    turn_index=turn_index,
                    mode="FACT",
                    fact=fact_phrase,
                    topic=topic,
                ),
            )
        )
    if decision.fact_id == "__ACCESS_BOOL_YES__":
        if not canonical_query.place_ref:
            return RenderedResponse(text=_clarify_for_intent(IntentId.DID_YOU_HAVE_ACCESS))
        return RenderedResponse(
            text=_render_or_fallback(
                cfg=cfg,
                fallback="Yes, I had access.",
                ctx=PromptContext(
                    npc_id=npc_id,
                    scene_id=scene,
                    turn_index=turn_index,
                    mode="FACT",
                    fact="Yes, I had access",
                    topic=topic,
                ),
            )
        )

    if decision.fact_id and decision.fact_id in world.facts:
        fact = world.facts[decision.fact_id]
        if not _fact_fits_intent(canonical_query.intent_id, fact.fact_type):
            return RenderedResponse(
                text=_render_or_fallback(
                    cfg=cfg,
                    fallback=_clarify_for_intent(canonical_query.intent_id),
                    ctx=PromptContext(
                        npc_id=npc_id,
                        scene_id=scene,
                        turn_index=turn_index,
                        mode="CLARIFY",
                        topic=topic,
                    ),
                )
            )
        if not _answer_shape_valid(canonical_query=canonical_query, fact=fact):
            return RenderedResponse(
                text=_render_or_fallback(
                    cfg=cfg,
                    fallback=_clarify_for_intent(canonical_query.intent_id),
                    ctx=PromptContext(
                        npc_id=npc_id,
                        scene_id=scene,
                        turn_index=turn_index,
                        mode="CLARIFY",
                        topic=topic,
                    ),
                )
            )
        fact_phrase = _fact_phrase(
            fact_type=fact.fact_type,
            fact_value=fact.value,
            scene_id=scene,
            npc_id=npc_id,
            turn_index=turn_index,
        )
        return RenderedResponse(
            text=_render_or_fallback(
                cfg=cfg,
                fallback=f"{fact_phrase}.",
                ctx=PromptContext(
                    npc_id=npc_id,
                    scene_id=scene,
                    turn_index=turn_index,
                    mode="FACT",
                    fact=fact_phrase,
                    topic=topic,
                ),
            )
        )

    return RenderedResponse(text="I don't know.")


def _render_or_fallback(*, cfg: PromptConfig | None, fallback: str, ctx: PromptContext) -> str:
    if cfg is None:
        return fallback
    try:
        rendered = render_text(cfg, ctx)
        return rendered if rendered.strip() else fallback
    except Exception:
        return fallback


@lru_cache(maxsize=1)
def _prompt_cfg() -> PromptConfig | None:
    content_dir = Path(__file__).resolve().parents[3] / "content"
    try:
        return load_prompt_config(content_dir)
    except PromptingError:
        return None


@lru_cache(maxsize=1)
def _voice_profiles() -> dict[str, Any] | None:
    voices_path = Path(__file__).resolve().parents[3] / "content" / "voices.yaml"
    if not voices_path.is_file():
        return None
    try:
        with open(voices_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _build_audio_hint(npc_id: str, decision_mode: DecisionMode) -> AudioHint | None:
    cfg = _voice_profiles()
    if cfg is None:
        return None
    profiles = cfg.get("profiles", {})
    npc_key = str(npc_id or "").strip().upper()
    profile = profiles.get(npc_key)
    if profile is None:
        return None
    emotion_map = cfg.get("emotion_map", {})
    emotion_hint = emotion_map.get(decision_mode.value, "neutral")
    base_speed = float(profile.get("base_speed", 1.0))
    adjustments = profile.get("adjustments", {}).get(emotion_hint, {})
    speed = float(adjustments.get("speed", base_speed))
    return AudioHint(
        voice_id=str(profile.get("voice_id", "default")),
        emotion_hint=emotion_hint,
        speed=speed,
    )


def fact_phrase_for(*, fact_type: str, fact_value: Any, scene_id: str, npc_id: str, turn_index: int) -> str:
    """Public accessor for fact phrase rendering. Used by LLM prompt builder."""
    return _fact_phrase(fact_type=fact_type, fact_value=fact_value, scene_id=scene_id, npc_id=npc_id, turn_index=turn_index)


def _fact_phrase(*, fact_type: str, fact_value: Any, scene_id: str, npc_id: str, turn_index: int) -> str:
    variants = _fact_variants(fact_type=fact_type, fact_value=fact_value, speaker_npc_id=npc_id)
    if len(variants) == 1:
        return variants[0]
    idx = _rotating_index(
        size=len(variants),
        stable_key=f"{scene_id}|{npc_id}|{fact_type}|{_stable_fact_material(fact_value)}",
        turn_index=turn_index,
    )
    return variants[idx]


def _fact_variants(*, fact_type: str, fact_value: Any, speaker_npc_id: str) -> tuple[str, ...]:
    payload = fact_value if isinstance(fact_value, dict) else {}
    value = _humanize_fact_value(fact_value)
    raw = str(fact_value or "").strip()
    if not value:
        return ("",)
    ft = str(fact_type or "").strip().lower()

    if ft == "time":
        when = _payload_text(payload, "time", fallback=value)
        return (
            when,
            f"At {when}",
            f"{when}, on the dot",
            f"Right around {when}",
        )
    if ft in {"access", "access_method"}:
        where = _payload_text(payload, "where", fallback="")
        method = _payload_text(payload, "method", fallback=value)
        where_phrase = where.replace("_", " ").lower() if where else ""
        if where_phrase:
            return (
                f"Access route was {method} at the {where_phrase}",
                f"The {where_phrase} used {method}",
                f"{method} access at the {where_phrase}",
            )
        return (
            value,
            f"Access route: {value}",
            f"The access point was {value}",
        )
    if ft in {"linkage", "presence"}:
        who = _payload_text(payload, "who", fallback="")
        where = _payload_text(payload, "where", fallback="")
        when = _payload_text(payload, "when", fallback="")
        if who and where:
            who_text = who.replace("_", " ").title()
            where_text = where.replace("_", " ").lower()
            when_suffix = f" at {when}" if when else ""
            if who == speaker_npc_id:
                return (
                    f"I was at the {where_text}{when_suffix}",
                    f"I was by the {where_text}{when_suffix}",
                )
            return (
                f"{who_text} was at the {where_text}{when_suffix}",
                f"I saw {who_text} near the {where_text}{when_suffix}",
                f"{who_text} was by the {where_text}{when_suffix}",
            )
        subject, location = _parse_present_at(raw)
        if subject and location:
            return (
                f"{subject} was at the {location}",
                f"I saw {subject} near the {location}",
                f"{subject} was by the {location}",
            )
        return (
            value,
            f"That points to {value}",
            f"{value}. That's what I know",
        )
    if ft == "witness":
        witness = _payload_text(payload, "witness", fallback="")
        who = _payload_text(payload, "who", fallback="")
        where = _payload_text(payload, "where", fallback="")
        when = _payload_text(payload, "when", fallback="")
        if witness and who and where:
            witness_text = witness.replace("_", " ").title()
            who_text = who.replace("_", " ").title()
            where_text = where.replace("_", " ").lower()
            when_suffix = f" at {when}" if when else ""
            if witness == speaker_npc_id:
                return (
                    f"I saw {who_text} near the {where_text}{when_suffix}",
                    f"I placed {who_text} by the {where_text}{when_suffix}",
                )
            return (
                f"{witness_text} saw {who_text} near the {where_text}{when_suffix}",
                f"I heard {witness_text} place {who_text} by the {where_text}{when_suffix}",
            )
        return (value, f"Witness line: {value}")
    if ft == "object":
        obj = _payload_text(payload, "object", fallback=value)
        obj_text = obj.replace("_", " ").lower()
        return (
            obj_text,
            f"The object was {obj_text}",
        )
    if ft == "action":
        obj = _payload_text(payload, "object", fallback="")
        action = _payload_text(payload, "action", fallback=value)
        when = _payload_text(payload, "when", fallback="")
        who = _payload_text(payload, "who", fallback="")
        where = _payload_text(payload, "where", fallback="")
        if obj:
            obj_text = obj.replace("_", " ").lower()
            when_suffix = f" at {when}" if when else ""
            action_text = action.replace("_", " ").lower()
            if who == speaker_npc_id:
                where_suffix = f" in the {where.replace('_', ' ').lower()}" if where else ""
                return (
                    f"I {action_text} the {obj_text}{where_suffix}{when_suffix}",
                    f"I handled the {obj_text}{where_suffix}{when_suffix}",
                )
            return (
                f"{obj_text} was {action_text}{when_suffix}",
                f"The {obj_text} got {action_text}{when_suffix}",
            )
        return (
            value,
            f"The action was {value}",
        )
    return (value,)


def _rotating_index(*, size: int, stable_key: str, turn_index: int) -> int:
    digest = hashlib.sha256(stable_key.encode("utf-8")).digest()
    base = int.from_bytes(digest[:8], "big", signed=False) % size
    return (base + max(turn_index, 1) - 1) % size


def _humanize_fact_value(value: Any) -> str:
    if isinstance(value, dict):
        if "time" in value:
            return str(value.get("time", "")).strip()
        if "object" in value:
            return str(value.get("object", "")).strip().replace("_", " ").lower()
        if "method" in value:
            method = str(value.get("method", "")).strip().replace("_", " ").lower()
            where = str(value.get("where", "")).strip().replace("_", " ").lower()
            return f"{method} at {where}".strip()
        if "who" in value and "where" in value:
            who = str(value.get("who", "")).strip().replace("_", " ").title()
            where = str(value.get("where", "")).strip().replace("_", " ").lower()
            return f"{who} at {where}".strip()
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    text = str(value or "").strip()
    if not text:
        return text
    return text.replace("_", " ").lower()


def _parse_present_at(value: str) -> tuple[str | None, str | None]:
    raw = str(value or "").strip().upper()
    match = re.fullmatch(r"([A-Z0-9_]+)_PRESENT_AT_([A-Z0-9_]+)", raw)
    if not match:
        return None, None
    subject_raw, location_raw = match.group(1), match.group(2)
    subject = subject_raw.replace("_", " ").title()
    location = location_raw.replace("_", " ").lower()
    return subject, location


def _fact_fits_intent(intent_id: IntentId, fact_type: str) -> bool:
    expected: dict[IntentId, set[str]] = {
        IntentId.WHEN_WAS: {"time"},
        IntentId.WHERE_WAS: {"linkage", "location", "presence"},
        IntentId.DID_YOU_SEE: {"linkage", "witness", "presence"},
        IntentId.WHO_WAS_WITH: {"linkage", "witness", "presence"},
        IntentId.DID_YOU_DO: {"action"},
    }
    allowed = expected.get(intent_id)
    if allowed is None:
        return True
    return str(fact_type or "").strip().lower() in allowed


def _clarify_for_intent(intent_id: IntentId) -> str:
    if intent_id == IntentId.WHERE_WAS:
        return "Where exactly do you mean?"
    if intent_id in {IntentId.DID_YOU_SEE, IntentId.WHO_WAS_WITH}:
        return "Who are you asking about?"
    if intent_id == IntentId.DID_YOU_HAVE_ACCESS:
        return "Access to what exactly?"
    if intent_id == IntentId.WHO_HAD_ACCESS:
        return "Who had access to which place?"
    return "Be specific."


def _people_with_access(world: WorldGraph, place_ref: str | None) -> list[str]:
    target = _normalize_place(place_ref) if place_ref else "SERVICE_DOOR"
    raw_people = world.access_graph.get(target, [])
    return [str(npc).replace("_", " ").title() for npc in raw_people]


def _normalize_place(place_ref: str) -> str:
    text = str(place_ref or "").strip().upper().replace(" ", "_")
    if not text:
        return "SERVICE_DOOR"
    if "SERVICE" in text and "DOOR" in text:
        return "SERVICE_DOOR"
    if "BOARDROOM" in text:
        return "BOARDROOM"
    if "ARCHIVE" in text:
        return "ARCHIVE"
    return text


def _stable_fact_material(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value or "")


def _payload_text(payload: dict[str, Any], key: str, *, fallback: str = "") -> str:
    raw = payload.get(key, fallback) if isinstance(payload, dict) else fallback
    return str(raw or "").strip()


def _answer_shape_valid(*, canonical_query: CanonicalQuery, fact: Any) -> bool:
    payload = fact.value if isinstance(getattr(fact, "value", None), dict) else {}
    if not isinstance(payload, dict):
        payload = {}
    intent = canonical_query.intent_id
    if intent == IntentId.WHERE_WAS:
        return bool(canonical_query.place_ref or payload.get("where"))
    if intent == IntentId.WHEN_WAS:
        return bool(canonical_query.time_ref or payload.get("when") or payload.get("time"))
    if intent == IntentId.DID_YOU_SEE:
        return bool(payload.get("who") or payload.get("witness"))
    if intent == IntentId.WHO_HAD_ACCESS:
        return bool(canonical_query.place_ref)
    if intent == IntentId.DID_YOU_HAVE_ACCESS:
        return bool(canonical_query.place_ref)
    return True


def _intent_bucket(intent_id: IntentId) -> str:
    if intent_id in {IntentId.DID_YOU_SEE, IntentId.WHO_WAS_WITH}:
        return "witness"
    if intent_id in {IntentId.WHO_HAD_ACCESS, IntentId.DID_YOU_HAVE_ACCESS}:
        return "access"
    if intent_id == IntentId.DID_YOU_DO:
        return "action"
    return "default"


def _refuse_text(*, intent_id: IntentId, persona_key: str) -> str:
    bucket = _intent_bucket(intent_id)
    by_intent = _REFUSE_BY_INTENT.get(bucket, {})
    return by_intent.get(persona_key, _REFUSE_STYLE.get(persona_key, "I can't answer that."))


def _dont_know_text(*, intent_id: IntentId, persona_key: str) -> str:
    bucket = _intent_bucket(intent_id)
    by_intent = _DONT_KNOW_BY_INTENT.get(bucket, {})
    return by_intent.get(persona_key, _DONT_KNOW_STYLE.get(persona_key, "I don't know."))
