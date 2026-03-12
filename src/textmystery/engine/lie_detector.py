"""Lie Detector game state, floor generation, and judgment.

Uses the Persona system for characters — no dependency on
TextMystery's mystery world graph.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum

from .persona import Persona, PersonaFact, render_persona_statement
from .truth_policy import TruthPolicy, TruthPolicyKind, should_be_truthful


class GameOutcome(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    WIN = "WIN"
    GAME_OVER = "GAME_OVER"


class PowerUpKind(str, Enum):
    OATH_STONE = "OATH_STONE"
    ECHO = "ECHO"
    REVEAL = "REVEAL"


@dataclass(frozen=True)
class FloorNpc:
    """Character assigned to a Lie Detector floor."""

    persona: Persona
    policy: TruthPolicy
    statement_fact: PersonaFact
    statement_text: str
    statement_is_true: bool

    @property
    def npc_id(self) -> str:
        return self.persona.persona_id

    @property
    def display_name(self) -> str:
        return self.persona.display_name


@dataclass(frozen=True)
class InterviewTurn:
    question_index: int
    raw_question: str
    response_text: str
    topic: str
    must_lie: bool


@dataclass
class FloorState:
    floor_number: int
    npc: FloorNpc
    questions_asked: int = 0
    max_questions: int = 5
    interview_log: list[InterviewTurn] = field(default_factory=list)
    statement_issued: bool = False
    judged: bool = False


@dataclass
class LieDetectorState:
    """Complete game state for a Lie Detector run."""

    current_floor: int = 1
    total_floors: int = 7
    streak: int = 0
    power_ups: list[PowerUpKind] = field(default_factory=list)
    outcome: GameOutcome = GameOutcome.IN_PROGRESS

    @property
    def is_game_over(self) -> bool:
        return self.outcome != GameOutcome.IN_PROGRESS


def _floor_rng_int(seed: int, floor_number: int, slot: str) -> int:
    """Deterministic integer from seed + floor + slot. No random module."""
    material = f"{seed}|floor{floor_number}|{slot}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest()[:8], 16)


# All topics used by TOPIC_SPLIT policy
_ALL_TOPICS = [
    "favorite_color", "hometown", "pet", "hobby",
    "job", "food", "music", "travel",
]


def generate_floors(
    seed: int,
    personas: list[Persona],
    total_floors: int = 7,
    policy_sequence: list[str] | None = None,
) -> list[FloorNpc]:
    """Generate deterministic persona + policy assignments for each floor.

    Uses sha256-based selection (no random module) for full determinism.
    """
    default_policies = [
        TruthPolicyKind.ALWAYS_TRUTH,
        TruthPolicyKind.ALWAYS_LIE,
        TruthPolicyKind.ALWAYS_TRUTH,
        TruthPolicyKind.HALF_AND_HALF,
        TruthPolicyKind.ALWAYS_LIE,
        TruthPolicyKind.TOPIC_SPLIT,
        TruthPolicyKind.ALWAYS_TRUTH,
    ]

    floor_npcs: list[FloorNpc] = []
    last_persona_idx: int | None = None

    for floor_num in range(1, total_floors + 1):
        # Pick persona, avoiding consecutive repeats
        persona_idx = -1
        for attempt in range(4):
            slot = f"npc_v{attempt}" if attempt > 0 else "npc"
            persona_idx = _floor_rng_int(seed, floor_num, slot) % len(personas)
            if persona_idx != last_persona_idx or len(personas) == 1:
                break
        last_persona_idx = persona_idx
        persona = personas[persona_idx]

        # Policy assignment
        if policy_sequence and floor_num <= len(policy_sequence):
            policy_kind = TruthPolicyKind(policy_sequence[floor_num - 1])
        else:
            policy_kind = default_policies[(floor_num - 1) % len(default_policies)]

        policy_seed = _floor_rng_int(seed, floor_num, "policy_seed")

        truth_topics: tuple[str, ...] = ()
        lie_topics: tuple[str, ...] = ()
        if policy_kind == TruthPolicyKind.TOPIC_SPLIT:
            split_val = _floor_rng_int(seed, floor_num, "topic_split") % 3 + 1
            truth_topics = tuple(_ALL_TOPICS[:split_val])
            lie_topics = tuple(_ALL_TOPICS[split_val:])

        policy = TruthPolicy(
            kind=policy_kind,
            seed=policy_seed,
            truth_topics=truth_topics,
            lie_topics=lie_topics,
        )

        # Statement: pick a fact from this persona
        fact_idx = _floor_rng_int(seed, floor_num, "fact") % len(persona.facts)
        statement_fact = persona.facts[fact_idx]

        # Statement truthfulness follows the persona's policy (meta-level)
        statement_is_true = should_be_truthful(
            policy, question_index=5, surface_id="META",
        )
        statement_text = render_persona_statement(
            persona, statement_fact, statement_is_true, seed, floor_num,
        )

        floor_npcs.append(FloorNpc(
            persona=persona,
            policy=policy,
            statement_fact=statement_fact,
            statement_text=statement_text,
            statement_is_true=statement_is_true,
        ))

    return floor_npcs


def judge_statement(
    state: LieDetectorState,
    floor: FloorState,
    player_says_true: bool,
) -> tuple[bool, int]:
    """Player judges the NPC's statement. Returns (correct, delta_floors).

    Statement truth is determined from persona facts (via FloorNpc.statement_is_true),
    NOT from LLM output. This is the single source of truth for judgment.
    """
    correct = (player_says_true == floor.npc.statement_is_true)

    if correct:
        early_solve = floor.questions_asked < floor.max_questions
        delta = 2 if early_solve else 1
        state.streak += 1
        if state.streak >= 3 and state.streak % 3 == 0:
            state.power_ups.append(PowerUpKind.OATH_STONE)
    else:
        delta = -1
        state.streak = 0

    state.current_floor += delta

    if state.current_floor < 1:
        state.current_floor = 0
        state.outcome = GameOutcome.GAME_OVER
    elif state.current_floor >= state.total_floors:
        state.current_floor = state.total_floors
        state.outcome = GameOutcome.WIN

    floor.judged = True
    return correct, delta
