from __future__ import annotations

import hashlib
from typing import Any

from .types import CanonicalQuery, IntentId, SurfaceId


_INTENT_KEYWORDS: dict[IntentId, tuple[str, ...]] = {
    IntentId.WHEN_WAS: ("when", "time", "clock", "timestamp"),
    IntentId.WHERE_WAS: ("where", "location", "room", "office", "hall", "door"),
    IntentId.DID_YOU_HAVE_ACCESS: ("access", "badge", "keycard", "key", "permission"),
    IntentId.WHO_HAD_ACCESS: ("who had access", "who could access", "who can access"),
    IntentId.DID_YOU_SEE: ("did you see", "saw", "witness", "notice"),
    IntentId.WHO_WAS_WITH: ("with who", "who was with", "together", "accompanied"),
    IntentId.DID_YOU_DO: ("did you", "handle", "touch", "move", "open"),
    IntentId.WHAT_DO_YOU_KNOW_ABOUT: ("what do you know", "tell me about", "anything on"),
    IntentId.META_REPEAT: ("repeat", "again", "say that again"),
}

_INTENT_TO_SURFACE: dict[IntentId, SurfaceId] = {
    IntentId.WHERE_WAS: SurfaceId.SURF_LOCATION,
    IntentId.WHEN_WAS: SurfaceId.SURF_TIME,
    IntentId.DID_YOU_SEE: SurfaceId.SURF_WITNESS,
    IntentId.DID_YOU_HAVE_ACCESS: SurfaceId.SURF_ACCESS,
    IntentId.DID_YOU_DO: SurfaceId.SURF_OBJECT,
    IntentId.WHO_HAD_ACCESS: SurfaceId.SURF_ACCESS,
    IntentId.WHO_WAS_WITH: SurfaceId.SURF_RELATIONSHIP,
    IntentId.WHAT_DO_YOU_KNOW_ABOUT: SurfaceId.SURF_META,
    IntentId.META_REPEAT: SurfaceId.SURF_META,
    IntentId.UNCLASSIFIED_AMBIGUOUS: SurfaceId.SURF_UNKNOWN,
}

_PRIORITY: dict[IntentId, int] = {
    IntentId.WHEN_WAS: 1,
    IntentId.WHERE_WAS: 1,
    IntentId.DID_YOU_HAVE_ACCESS: 2,
    IntentId.WHO_HAD_ACCESS: 2,
    IntentId.DID_YOU_SEE: 3,
    IntentId.WHO_WAS_WITH: 3,
    IntentId.DID_YOU_DO: 4,
    IntentId.WHAT_DO_YOU_KNOW_ABOUT: 5,
    IntentId.META_REPEAT: 6,
}

_PHRASE_FIRST_RULES: tuple[tuple[tuple[str, ...], IntentId, float], ...] = (
    (("who had access", "who could access", "who can access"), IntentId.WHO_HAD_ACCESS, 1.0),
    (("did you have access",), IntentId.DID_YOU_HAVE_ACCESS, 1.0),
    (("who did you see", "did you see"), IntentId.DID_YOU_SEE, 1.0),
    (("who can confirm", "who confirms", "who can verify", "who verifies"), IntentId.WHO_WAS_WITH, 1.0),
    (("who was with", "with who"), IntentId.WHO_WAS_WITH, 1.0),
    (("where were you",), IntentId.WHERE_WAS, 1.0),
    (("when were you", "what time"), IntentId.WHEN_WAS, 1.0),
)


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for token in keywords if token in text)


def _normalized_confidence(score: int, keywords: tuple[str, ...]) -> float:
    if score <= 0 or not keywords:
        return 0.0
    return max(0.0, min(1.0, float(score) / float(len(keywords))))


def classify_question(raw_text: str, npc_ids: list[str], scene_context: dict[str, Any]) -> CanonicalQuery:
    """Map free text to canonical query tags deterministically.

    Confidence is classifier-only and independent from world/transcript state.
    """
    del npc_ids  # reserved for future entity extraction rules
    del scene_context
    raw = str(raw_text or "")
    lower = raw.strip().lower()
    raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if not lower:
        return CanonicalQuery(
            intent_id=IntentId.UNCLASSIFIED_AMBIGUOUS,
            surface_id=SurfaceId.SURF_UNKNOWN,
            confidence=0.0,
            raw_text_hash=raw_hash,
        )

    # Surface-probe intent is explicit and should not be overshadowed by access/time keywords.
    if any(token in lower for token in ("what do you know", "tell me about", "anything on")):
        return CanonicalQuery(
            intent_id=IntentId.WHAT_DO_YOU_KNOW_ABOUT,
            surface_id=SurfaceId.SURF_META,
            confidence=1.0 if "what do you know" in lower else 0.8,
            raw_text_hash=raw_hash,
        )
    for patterns, intent_id, confidence in _PHRASE_FIRST_RULES:
        if any(pattern in lower for pattern in patterns):
            place_ref = _extract_place_ref(lower)
            object_id = _extract_object_id(lower)
            if intent_id == IntentId.DID_YOU_HAVE_ACCESS and object_id and not place_ref:
                intent_id = IntentId.DID_YOU_DO
            return CanonicalQuery(
                intent_id=intent_id,
                surface_id=_INTENT_TO_SURFACE[intent_id],
                time_ref=_extract_time_ref(lower),
                place_ref=place_ref,
                object_id=object_id,
                confidence=confidence,
                raw_text_hash=raw_hash,
            )

    # Witness shorthand: short forms like "see near service door?" should resolve as witness.
    if ("see" in lower or "saw" in lower or "notice" in lower) and _extract_place_ref(lower):
        return CanonicalQuery(
            intent_id=IntentId.DID_YOU_SEE,
            surface_id=SurfaceId.SURF_WITNESS,
            time_ref=_extract_time_ref(lower),
            place_ref=_extract_place_ref(lower),
            object_id=_extract_object_id(lower),
            confidence=0.75,
            raw_text_hash=raw_hash,
        )

    candidates: list[tuple[int, int, str, str, IntentId, SurfaceId, float]] = []
    for intent_id, keywords in _INTENT_KEYWORDS.items():
        score = _keyword_score(lower, keywords)
        if score <= 0:
            continue
        surface_id = _INTENT_TO_SURFACE[intent_id]
        priority = _PRIORITY[intent_id]
        confidence = _normalized_confidence(score, keywords)
        # Sort keys enforce deterministic tie-break sequence:
        # priority -> intent -> surface -> object_id (empty for v1 classifier).
        candidates.append((priority, -score, intent_id.value, surface_id.value, intent_id, surface_id, confidence))

    if not candidates:
        return CanonicalQuery(
            intent_id=IntentId.UNCLASSIFIED_AMBIGUOUS,
            surface_id=SurfaceId.SURF_UNKNOWN,
            confidence=0.0,
            raw_text_hash=raw_hash,
        )

    candidates.sort(key=lambda row: (row[0], row[1], row[2], row[3], ""))
    _, _, _, _, chosen_intent, chosen_surface, chosen_confidence = candidates[0]
    place_ref = _extract_place_ref(lower)
    object_id = _extract_object_id(lower)
    if chosen_intent == IntentId.DID_YOU_HAVE_ACCESS and object_id and not place_ref:
        chosen_intent = IntentId.DID_YOU_DO
        chosen_surface = _INTENT_TO_SURFACE[chosen_intent]
    return CanonicalQuery(
        intent_id=chosen_intent,
        surface_id=chosen_surface,
        time_ref=_extract_time_ref(lower),
        place_ref=place_ref,
        object_id=object_id,
        confidence=chosen_confidence,
        raw_text_hash=raw_hash,
    )


def _extract_time_ref(lower_text: str) -> str | None:
    if "11:03" in lower_text:
        return "11:03"
    if "alarm" in lower_text:
        return "ALARM_TIME"
    return None


def _extract_place_ref(lower_text: str) -> str | None:
    if "service door" in lower_text:
        return "SERVICE_DOOR"
    if "boardroom" in lower_text:
        return "BOARDROOM"
    if "archive" in lower_text:
        return "ARCHIVE"
    return None


def _extract_object_id(lower_text: str) -> str | None:
    if "audit drive" in lower_text or ("audit" in lower_text and "drive" in lower_text):
        return "AUDIT_DRIVE"
    if "boardroom feed" in lower_text or "feed" in lower_text:
        return "BOARDROOM_FEED"
    return None
