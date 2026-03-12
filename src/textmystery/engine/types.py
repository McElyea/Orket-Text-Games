from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class Fact:
    fact_id: str
    fact_type: str
    value: Any


class DecisionMode(str, Enum):
    ANSWER = "ANSWER"
    REFUSE = "REFUSE"
    DONT_KNOW = "DONT_KNOW"


class IntentId(str, Enum):
    WHERE_WAS = "WHERE_WAS"
    WHEN_WAS = "WHEN_WAS"
    DID_YOU_SEE = "DID_YOU_SEE"
    DID_YOU_HAVE_ACCESS = "DID_YOU_HAVE_ACCESS"
    DID_YOU_DO = "DID_YOU_DO"
    WHO_HAD_ACCESS = "WHO_HAD_ACCESS"
    WHO_WAS_WITH = "WHO_WAS_WITH"
    WHAT_DO_YOU_KNOW_ABOUT = "WHAT_DO_YOU_KNOW_ABOUT"
    META_REPEAT = "META_REPEAT"
    UNCLASSIFIED_AMBIGUOUS = "UNCLASSIFIED_AMBIGUOUS"


class SurfaceId(str, Enum):
    SURF_TIME = "SURF_TIME"
    SURF_ACCESS = "SURF_ACCESS"
    SURF_LOCATION = "SURF_LOCATION"
    SURF_WITNESS = "SURF_WITNESS"
    SURF_OBJECT = "SURF_OBJECT"
    SURF_RELATIONSHIP = "SURF_RELATIONSHIP"
    SURF_MOTIVE = "SURF_MOTIVE"
    SURF_ALIBI = "SURF_ALIBI"
    SURF_META = "SURF_META"
    SURF_UNKNOWN = "SURF_UNKNOWN"


@dataclass(frozen=True)
class AnswerDecision:
    mode: DecisionMode
    fact_id: str | None = None
    refusal_reason: str | None = None


@dataclass(frozen=True)
class CanonicalQuery:
    intent_id: IntentId
    surface_id: SurfaceId
    subject_id: str | None = None
    object_id: str | None = None
    time_ref: str | None = None
    place_ref: str | None = None
    polarity: str | None = None
    confidence: float = 0.0
    raw_text_hash: str = ""


@dataclass(frozen=True)
class AudioHint:
    """Hint for audio synthesis. Pure data — no SDK dependency."""
    voice_id: str
    emotion_hint: str = "neutral"
    speed: float = 1.0


@dataclass(frozen=True)
class InteractionResult:
    decision: AnswerDecision
    response_text: str
    canonical_query: CanonicalQuery | dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TranscriptTurn:
    timestamp: int
    npc_id: str
    raw_question: str
    canonical_query: CanonicalQuery | dict[str, Any]
    decision: DecisionMode
    npc_response_text: str
    companion_line: str | None = None


@dataclass(frozen=True)
class RevealGraph:
    culprit_npc_id: str
    primary_crime_id: str
    refusal_causes: dict[str, str] = field(default_factory=dict)
    facts: dict[str, Fact] = field(default_factory=dict)


@dataclass(frozen=True)
class CompanionMemory:
    temperament: str = "nice"
    hint_threshold: int = 3
    voice_id: str = "default"
    sessions_count: int = 0
    last_played_at: int | None = None
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorldGraph:
    scene_template_id: str
    selected_npc_ids: tuple[str, ...]
    culprit_npc_id: str
    primary_crime_id: str
    facts: dict[str, Fact] = field(default_factory=dict)
    npc_knowledge: dict[str, set[str]] = field(default_factory=dict)
    npc_guards: dict[str, set[str]] = field(default_factory=dict)
    npc_secrets: dict[str, str] = field(default_factory=dict)
    access_graph: dict[str, list[str]] = field(default_factory=dict)
    lead_unlocks: dict[str, tuple[str, ...]] = field(default_factory=dict)
    time_anchors: tuple[str, ...] = field(default_factory=tuple)
    access_anchors: tuple[str, ...] = field(default_factory=tuple)
    linkage_anchors: tuple[str, ...] = field(default_factory=tuple)
    digest: str = ""


@dataclass(frozen=True)
class RunHeader:
    seed: int
    scene_id: str
    npc_ids: tuple[str, ...]
    difficulty: str
    content_version: str
    generator_version: str
    world_digest: str
