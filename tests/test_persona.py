"""Tests for the Lie Detector persona system."""
from __future__ import annotations

from textmystery.engine.persona import (
    Persona,
    PersonaFact,
    classify_topic,
    generate_personas,
    load_archetypes,
    render_persona_statement,
    resolve_persona_answer,
)


class TestGeneratePersonas:
    def test_deterministic_same_seed(self):
        p1 = generate_personas(seed=42, count=8)
        p2 = generate_personas(seed=42, count=8)
        for a, b in zip(p1, p2):
            assert a.persona_id == b.persona_id
            assert a.display_name == b.display_name
            assert a.archetype_id == b.archetype_id
            assert a.backstory == b.backstory
            assert a.facts == b.facts

    def test_different_seeds_differ(self):
        p1 = generate_personas(seed=42, count=8)
        p2 = generate_personas(seed=99, count=8)
        names1 = {p.display_name for p in p1}
        names2 = {p.display_name for p in p2}
        assert names1 != names2

    def test_correct_count(self):
        personas = generate_personas(seed=42, count=12)
        assert len(personas) == 12

    def test_unique_names(self):
        personas = generate_personas(seed=42, count=12)
        names = [p.display_name for p in personas]
        assert len(names) == len(set(names))

    def test_each_has_facts(self):
        personas = generate_personas(seed=42, count=8)
        for p in personas:
            assert len(p.facts) >= 6
            for f in p.facts:
                assert f.topic
                assert f.display_topic
                assert f.value

    def test_persona_id_format(self):
        personas = generate_personas(seed=42, count=4)
        for p in personas:
            assert p.persona_id == p.persona_id.upper()
            assert "_" in p.persona_id

    def test_backstory_contains_name(self):
        personas = generate_personas(seed=42, count=4)
        for p in personas:
            assert p.display_name in p.backstory


class TestClassifyTopic:
    def test_color(self):
        assert classify_topic("What is your favorite color?") == "favorite_color"

    def test_hometown(self):
        assert classify_topic("Where are you from?") == "hometown"

    def test_pet(self):
        assert classify_topic("Do you have a pet?") == "pet"

    def test_hobby(self):
        assert classify_topic("What do you do for fun?") == "hobby"

    def test_job(self):
        assert classify_topic("What do you do for a living?") == "job"

    def test_food(self):
        assert classify_topic("What's your favorite food?") == "food"

    def test_music(self):
        assert classify_topic("What kind of music do you listen to?") == "music"

    def test_fear(self):
        assert classify_topic("What are you afraid of?") == "fear"

    def test_sibling(self):
        assert classify_topic("Do you have any siblings?") == "sibling"

    def test_morning(self):
        assert classify_topic("What's your morning routine?") == "morning_routine"

    def test_childhood(self):
        assert classify_topic("What's your favorite childhood memory?") == "childhood_memory"

    def test_travel(self):
        assert classify_topic("Where would you travel to?") == "travel"

    def test_unknown(self):
        assert classify_topic("How many fingers am I holding up?") == "unknown"


class TestResolvePersonaAnswer:
    def _make_persona(self) -> Persona:
        return Persona(
            persona_id="TEST_NPC",
            display_name="Test Npc",
            archetype_id="LAID_BACK",
            backstory="Test backstory.",
            facts=(
                PersonaFact(topic="favorite_color", display_topic="favorite color", value="blue"),
                PersonaFact(topic="hometown", display_topic="hometown", value="Portland"),
            ),
        )

    def test_truthful_known_topic(self):
        p = self._make_persona()
        answer = resolve_persona_answer(p, "favorite_color", must_lie=False, question_index=0)
        assert "blue" in answer

    def test_truthful_unknown_topic(self):
        p = self._make_persona()
        answer = resolve_persona_answer(p, "pet", must_lie=False, question_index=0)
        assert "blue" not in answer
        assert "don't" in answer.lower() or "not" in answer.lower() or "can't" in answer.lower()

    def test_lying_known_topic(self):
        p = self._make_persona()
        answer = resolve_persona_answer(p, "favorite_color", must_lie=True, question_index=0)
        assert "blue" not in answer  # should not reveal the truth

    def test_lying_unknown_topic(self):
        p = self._make_persona()
        answer = resolve_persona_answer(p, "pet", must_lie=True, question_index=0)
        # Unknown topic while lying still returns don't-know
        assert answer

    def test_archetype_banks_used(self):
        from textmystery.engine.persona import PersonaArchetype

        p = self._make_persona()
        arch = PersonaArchetype(
            archetype_id="SHARP_WIT",
            description="Quick.",
            max_words=12,
            banks={
                "dont_know": ["No clue.", "Beats me."],
                "lie": ["Wrong tree.", "Not even close."],
                "refuse": ["Next question."],
            },
        )
        answer = resolve_persona_answer(p, "pet", must_lie=False, question_index=0, archetype=arch)
        assert answer in ["No clue.", "Beats me."]

    def test_lie_with_archetype(self):
        from textmystery.engine.persona import PersonaArchetype

        p = self._make_persona()
        arch = PersonaArchetype(
            archetype_id="SHARP_WIT",
            description="Quick.",
            max_words=12,
            banks={
                "dont_know": ["No clue."],
                "lie": ["Wrong tree.", "Not even close."],
                "refuse": ["Next question."],
            },
        )
        answer = resolve_persona_answer(p, "favorite_color", must_lie=True, question_index=0, archetype=arch)
        assert answer in ["Wrong tree.", "Not even close."]


class TestRenderPersonaStatement:
    def test_true_statement(self):
        fact = PersonaFact(topic="favorite_color", display_topic="favorite color", value="blue")
        p = Persona(
            persona_id="TEST", display_name="Test",
            archetype_id="LAID_BACK", backstory="Test.",
            facts=(fact,),
        )
        stmt = render_persona_statement(p, fact, is_true=True, seed=42, floor_number=1)
        assert "blue" in stmt
        assert "favorite color" in stmt

    def test_false_statement_no_true_value(self):
        fact = PersonaFact(topic="favorite_color", display_topic="favorite color", value="blue")
        p = Persona(
            persona_id="TEST", display_name="Test",
            archetype_id="LAID_BACK", backstory="Test.",
            facts=(fact,),
        )
        stmt = render_persona_statement(p, fact, is_true=False, seed=42, floor_number=1)
        assert "blue" not in stmt
        assert "favorite color" in stmt

    def test_false_statement_deterministic(self):
        fact = PersonaFact(topic="hometown", display_topic="hometown", value="Portland")
        p = Persona(
            persona_id="TEST", display_name="Test",
            archetype_id="LAID_BACK", backstory="Test.",
            facts=(fact,),
        )
        s1 = render_persona_statement(p, fact, is_true=False, seed=42, floor_number=1)
        s2 = render_persona_statement(p, fact, is_true=False, seed=42, floor_number=1)
        assert s1 == s2
