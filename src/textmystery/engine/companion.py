from __future__ import annotations

import hashlib
from typing import Any

from .types import CanonicalQuery, CompanionMemory, DecisionMode, SurfaceId, TranscriptTurn


def maybe_nudge(
    transcript: list[TranscriptTurn],
    settings: dict[str, Any],
    memory: CompanionMemory,
) -> str | None:
    """Return optional transcript-only companion nudge after deterministic stall threshold."""
    threshold_raw = settings.get("hint_threshold", memory.hint_threshold)
    try:
        threshold = max(1, int(threshold_raw))
    except (TypeError, ValueError):
        threshold = max(1, int(memory.hint_threshold))

    stall_count = 0
    last_surface = SurfaceId.SURF_UNKNOWN.value
    last_npc = "that suspect"
    for turn in transcript:
        is_stall = turn.decision in {DecisionMode.DONT_KNOW, DecisionMode.REFUSE}
        cq = turn.canonical_query
        surface = _surface_id(cq)
        last_surface = surface
        last_npc = str(turn.npc_id or last_npc)
        if surface == SurfaceId.SURF_UNKNOWN.value:
            is_stall = True
        if is_stall:
            stall_count += 1

    if stall_count >= threshold:
        return _actionable_nudge(transcript, last_npc=last_npc, last_surface=last_surface)
    return None


def _surface_id(query: CanonicalQuery | dict[str, Any]) -> str:
    if isinstance(query, CanonicalQuery):
        return query.surface_id.value
    if isinstance(query, dict):
        return str(query.get("surface_id") or SurfaceId.SURF_UNKNOWN.value)
    return SurfaceId.SURF_UNKNOWN.value


def _actionable_nudge(transcript: list[TranscriptTurn], *, last_npc: str, last_surface: str) -> str:
    prompts = _prompt_examples(last_npc=last_npc, surface_id=last_surface)
    idx = _stable_index(transcript, len(prompts))
    pick = prompts[idx]
    return f"Try: \"{pick[0]}\"  Then: \"{pick[1]}\""


def _prompt_examples(*, last_npc: str, surface_id: str) -> tuple[tuple[str, str], ...]:
    npc = str(last_npc or "that suspect")
    by_surface: dict[str, tuple[tuple[str, str], ...]] = {
        SurfaceId.SURF_TIME.value: (
            (f"Where were you at 11:03, {npc}?", "Who can confirm that time?"),
            ("When did the alarm hit live TV?", "Who was with you then?"),
        ),
        SurfaceId.SURF_ACCESS.value: (
            ("Who had access to the service door?", "Did you have keycard access?"),
            ("Who had access to the archive?", "Whose badge opened that route?"),
        ),
        SurfaceId.SURF_WITNESS.value: (
            ("Who did you see near the service door?", "Did you see Nadia Bloom there?"),
            ("Who was with you at 11:03?", "Did you notice Victor Slate?"),
        ),
    }
    default_prompts = (
        ("Where were you at 11:03?", "Who had access to the service door?"),
        ("Who did you see near the boardroom?", "What do you know about the audit drive?"),
    )
    return by_surface.get(surface_id, default_prompts)


def _stable_index(transcript: list[TranscriptTurn], size: int) -> int:
    if size <= 1:
        return 0
    if not transcript:
        return 0
    last = transcript[-1]
    material = f"{last.timestamp}|{last.npc_id}|{last.raw_question}|{last.decision.value}"
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False) % size
