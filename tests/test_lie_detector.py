from __future__ import annotations

import pytest

from textmystery.engine.lie_detector import (
    FloorNpc,
    FloorState,
    GameOutcome,
    LieDetectorState,
    PowerUpKind,
    generate_floors,
    judge_statement,
)
from textmystery.engine.persona import Persona, PersonaFact, generate_personas
from textmystery.engine.truth_policy import TruthPolicy, TruthPolicyKind


def _make_personas() -> list[Persona]:
    """Generate a small set of personas for testing."""
    return generate_personas(seed=42, count=4)


def _make_floor_npc(statement_is_true: bool = True) -> FloorNpc:
    fact = PersonaFact(topic="favorite_color", display_topic="favorite color", value="blue")
    persona = Persona(
        persona_id="TEST_NPC",
        display_name="Test Npc",
        archetype_id="LAID_BACK",
        backstory="Test backstory.",
        facts=(fact,),
    )
    return FloorNpc(
        persona=persona,
        policy=TruthPolicy(kind=TruthPolicyKind.ALWAYS_TRUTH),
        statement_fact=fact,
        statement_text="My favorite color is blue." if statement_is_true else "My favorite color is pink.",
        statement_is_true=statement_is_true,
    )


class TestFloorGeneration:
    def test_deterministic_given_same_seed(self):
        personas = _make_personas()
        floors_a = generate_floors(42, personas, total_floors=7)
        floors_b = generate_floors(42, personas, total_floors=7)
        assert len(floors_a) == len(floors_b) == 7
        for a, b in zip(floors_a, floors_b):
            assert a.npc_id == b.npc_id
            assert a.policy == b.policy
            assert a.statement_text == b.statement_text
            assert a.statement_is_true == b.statement_is_true

    def test_all_floors_have_personas(self):
        personas = _make_personas()
        persona_ids = {p.persona_id for p in personas}
        floors = generate_floors(42, personas, total_floors=5)
        assert len(floors) == 5
        for f in floors:
            assert f.npc_id in persona_ids
            assert f.display_name
            assert f.statement_text

    def test_policies_assigned(self):
        personas = _make_personas()
        floors = generate_floors(42, personas, total_floors=7)
        policy_kinds = {f.policy.kind for f in floors}
        assert len(policy_kinds) >= 2

    def test_different_seeds_produce_different_floors(self):
        personas = _make_personas()
        floors_a = generate_floors(1, personas, total_floors=7)
        floors_b = generate_floors(999, personas, total_floors=7)
        npcs_a = [f.npc_id for f in floors_a]
        npcs_b = [f.npc_id for f in floors_b]
        assert npcs_a != npcs_b or [f.statement_is_true for f in floors_a] != [f.statement_is_true for f in floors_b]

    def test_no_consecutive_repeat_persona(self):
        personas = _make_personas()
        floors = generate_floors(42, personas, total_floors=7)
        for i in range(len(floors) - 1):
            assert floors[i].npc_id != floors[i + 1].npc_id

    def test_statements_use_persona_facts(self):
        personas = _make_personas()
        floors = generate_floors(42, personas, total_floors=7)
        for f in floors:
            # Statement should reference a display topic from the persona's facts
            fact_topics = {fact.display_topic for fact in f.persona.facts}
            has_topic = any(topic in f.statement_text for topic in fact_topics)
            assert has_topic, f"Statement '{f.statement_text}' doesn't match any topic of {f.display_name}"


class TestJudgment:
    def test_correct_judgment_climbs_one(self):
        state = LieDetectorState(current_floor=3, total_floors=7)
        floor = FloorState(floor_number=3, npc=_make_floor_npc(statement_is_true=True), questions_asked=5)
        correct, delta = judge_statement(state, floor, player_says_true=True)
        assert correct is True
        assert delta == 1
        assert state.current_floor == 4

    def test_wrong_judgment_falls_one(self):
        state = LieDetectorState(current_floor=3, total_floors=7)
        floor = FloorState(floor_number=3, npc=_make_floor_npc(statement_is_true=True), questions_asked=5)
        correct, delta = judge_statement(state, floor, player_says_true=False)
        assert correct is False
        assert delta == -1
        assert state.current_floor == 2

    def test_early_solve_climbs_two(self):
        state = LieDetectorState(current_floor=3, total_floors=7)
        floor = FloorState(floor_number=3, npc=_make_floor_npc(statement_is_true=True), questions_asked=3)
        correct, delta = judge_statement(state, floor, player_says_true=True)
        assert correct is True
        assert delta == 2
        assert state.current_floor == 5

    def test_fall_below_floor_1_game_over(self):
        state = LieDetectorState(current_floor=1, total_floors=7)
        floor = FloorState(floor_number=1, npc=_make_floor_npc(statement_is_true=True), questions_asked=5)
        correct, delta = judge_statement(state, floor, player_says_true=False)
        assert correct is False
        assert state.outcome == GameOutcome.GAME_OVER
        assert state.current_floor == 0

    def test_reach_top_floor_win(self):
        state = LieDetectorState(current_floor=6, total_floors=7)
        floor = FloorState(floor_number=6, npc=_make_floor_npc(statement_is_true=True), questions_asked=5)
        correct, delta = judge_statement(state, floor, player_says_true=True)
        assert correct is True
        assert state.outcome == GameOutcome.WIN

    def test_streak_reset_on_wrong(self):
        state = LieDetectorState(current_floor=3, total_floors=7, streak=2)
        floor = FloorState(floor_number=3, npc=_make_floor_npc(statement_is_true=True), questions_asked=5)
        judge_statement(state, floor, player_says_true=False)
        assert state.streak == 0

    def test_streak_of_3_awards_oath_stone(self):
        state = LieDetectorState(current_floor=2, total_floors=10, streak=2)
        floor = FloorState(floor_number=2, npc=_make_floor_npc(statement_is_true=True), questions_asked=5)
        judge_statement(state, floor, player_says_true=True)
        assert state.streak == 3
        assert PowerUpKind.OATH_STONE in state.power_ups

    def test_false_statement_judged_false_is_correct(self):
        state = LieDetectorState(current_floor=3, total_floors=7)
        floor = FloorState(floor_number=3, npc=_make_floor_npc(statement_is_true=False), questions_asked=5)
        correct, delta = judge_statement(state, floor, player_says_true=False)
        assert correct is True
        assert delta == 1

    def test_floor_marked_judged(self):
        state = LieDetectorState(current_floor=3, total_floors=7)
        floor = FloorState(floor_number=3, npc=_make_floor_npc(statement_is_true=True), questions_asked=5)
        judge_statement(state, floor, player_says_true=True)
        assert floor.judged is True
