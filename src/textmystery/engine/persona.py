"""Persona system for The Lie Detector.

Self-contained character generation with simple, verifiable facts.
No dependency on TextMystery's mystery world graph.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PersonaFact:
    """A single verifiable fact about a persona."""

    topic: str            # e.g., "favorite_color"
    display_topic: str    # e.g., "favorite color"
    value: str            # e.g., "blue"


@dataclass(frozen=True)
class PersonaArchetype:
    """Personality voice for a persona."""

    archetype_id: str
    description: str
    max_words: int
    banks: dict[str, list[str]]  # dont_know, lie, refuse


@dataclass(frozen=True)
class Persona:
    """A self-contained character for The Lie Detector."""

    persona_id: str             # e.g., "DANA_CROSS"
    display_name: str           # e.g., "Dana Cross"
    archetype_id: str           # e.g., "LAID_BACK"
    backstory: str              # One-line flavor text
    facts: tuple[PersonaFact, ...]  # 6-10 verifiable facts


def _det_int(seed: int, *parts: str) -> int:
    """Deterministic integer from seed + parts. No random module."""
    material = f"{seed}|{'|'.join(parts)}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest()[:8], 16)


def _load_persona_content(content_path: Path | None = None) -> dict[str, Any]:
    """Load persona content pools from YAML."""
    if content_path is None:
        content_path = (
            Path(__file__).resolve().parents[3]
            / "content"
            / "lie_detector"
            / "personas.yaml"
        )
    with open(content_path) as f:
        return yaml.safe_load(f) or {}


def load_archetypes(content: dict[str, Any] | None = None) -> dict[str, PersonaArchetype]:
    """Load archetype definitions from content dict."""
    if content is None:
        content = _load_persona_content()
    archetypes: dict[str, PersonaArchetype] = {}
    for arch_id, arch_data in content.get("archetypes", {}).items():
        archetypes[arch_id] = PersonaArchetype(
            archetype_id=arch_id,
            description=arch_data.get("description", ""),
            max_words=arch_data.get("max_words", 14),
            banks=arch_data.get("banks", {}),
        )
    return archetypes


def generate_personas(
    seed: int,
    count: int = 12,
    content_path: Path | None = None,
) -> list[Persona]:
    """Generate deterministic personas from content pools.

    Uses sha256-based selection. No random module. Same seed = same personas.
    """
    content = _load_persona_content(content_path)

    first_names: list[str] = content.get("first_names", [])
    last_names: list[str] = content.get("last_names", [])
    archetype_ids: list[str] = list(content.get("archetypes", {}).keys())
    backstories: list[str] = content.get("backstories", [])
    topics_config: dict[str, Any] = content.get("topics", {})
    facts_per_persona: int = content.get("facts_per_persona", 8)

    all_topics = list(topics_config.keys())

    personas: list[Persona] = []
    used_name_pairs: set[tuple[int, int]] = set()

    for i in range(count):
        # Pick unique first + last name combo
        for attempt in range(20):
            slot = f"name_v{attempt}" if attempt > 0 else "name"
            first_idx = _det_int(seed, slot, str(i), "first") % len(first_names)
            last_idx = _det_int(seed, slot, str(i), "last") % len(last_names)
            pair = (first_idx, last_idx)
            if pair not in used_name_pairs:
                used_name_pairs.add(pair)
                break

        first = first_names[first_idx]
        last = last_names[last_idx]
        display_name = f"{first} {last}"
        persona_id = f"{first.upper()}_{last.upper()}"

        # Archetype
        arch_idx = _det_int(seed, str(i), "archetype") % len(archetype_ids)
        archetype_id = archetype_ids[arch_idx]

        # Backstory
        back_idx = _det_int(seed, str(i), "backstory") % len(backstories)
        backstory = backstories[back_idx].replace("{name}", display_name)

        # Select topics for this persona (deterministic shuffle via scoring)
        topic_scores = []
        for t in all_topics:
            score = _det_int(seed, str(i), "topic_score", t)
            topic_scores.append((score, t))
        topic_scores.sort()
        selected_topics = [t for _, t in topic_scores[:facts_per_persona]]

        # Generate facts
        facts: list[PersonaFact] = []
        for topic in selected_topics:
            t_config = topics_config[topic]
            values: list[str] = t_config.get("values", [])
            val_idx = _det_int(seed, str(i), "fact_val", topic) % len(values)
            facts.append(PersonaFact(
                topic=topic,
                display_topic=t_config.get("display", topic.replace("_", " ")),
                value=values[val_idx],
            ))

        personas.append(Persona(
            persona_id=persona_id,
            display_name=display_name,
            archetype_id=archetype_id,
            backstory=backstory,
            facts=tuple(facts),
        ))

    return personas


def classify_topic(raw_question: str) -> str:
    """Classify a player question into a topic string.

    Simple keyword matching. Returns the topic key or "unknown".
    """
    q = raw_question.lower().strip()

    # Direct topic keywords
    topic_keywords: dict[str, list[str]] = {
        "favorite_color": ["color", "colour"],
        "hometown": ["hometown", "home town", "where are you from",
                      "where do you live", "grew up", "where did you grow up",
                      "from where"],
        "pet": ["pet", "animal", "dog", "cat", "fish"],
        "hobby": ["hobby", "hobbies", "free time", "fun", "pastime",
                   "do for fun", "spare time", "like to do"],
        "job": ["job", "work", "occupation", "career", "profession",
                "living", "do for a living", "employed"],
        "food": ["food", "eat", "favorite food", "meal", "dish", "cuisine",
                 "hungry", "cook"],
        "music": ["music", "song", "band", "listen", "genre", "playlist",
                   "musician", "concert"],
        "travel": ["travel", "vacation", "trip", "visit", "destination",
                    "go to", "dream destination", "country"],
        "sibling": ["sibling", "brother", "sister", "siblings", "family",
                     "twin", "only child"],
        "fear": ["fear", "afraid", "scared", "phobia", "frighten",
                  "scare", "worst fear"],
        "morning_routine": ["morning", "wake up", "routine", "start your day",
                            "first thing"],
        "childhood_memory": ["childhood", "kid", "child", "grew up",
                             "remember from", "young", "memory", "memories"],
    }

    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in q:
                return topic

    return "unknown"


def resolve_persona_answer(
    persona: Persona,
    topic: str,
    must_lie: bool,
    question_index: int,
    archetype: PersonaArchetype | None = None,
) -> str:
    """Resolve a persona's answer for a topic.

    Returns the response text (template mode).
    """
    # Find matching fact
    fact = None
    for f in persona.facts:
        if f.topic == topic:
            fact = f
            break

    if fact is None:
        # Persona doesn't know about this topic
        if archetype and archetype.banks.get("dont_know"):
            bank = archetype.banks["dont_know"]
            return bank[question_index % len(bank)]
        return "I don't really have an answer for that."

    if must_lie:
        # Persona is lying — use lie template
        if archetype and archetype.banks.get("lie"):
            bank = archetype.banks["lie"]
            return bank[question_index % len(bank)]
        return "I don't think that's right."

    # Truthful answer
    return f"My {fact.display_topic} is {fact.value}."


def render_persona_statement(
    persona: Persona,
    fact: PersonaFact,
    is_true: bool,
    seed: int,
    floor_number: int,
) -> str:
    """Render a persona fact as a TRUE or FALSE statement.

    For false statements, picks an alternative value deterministically.
    """
    if is_true:
        return f"My {fact.display_topic} is {fact.value}."

    # Pick a false value from the content pools
    content = _load_persona_content()
    topic_config = content.get("topics", {}).get(fact.topic, {})
    false_values: list[str] = topic_config.get("false_values", [])

    if false_values:
        idx = _det_int(seed, str(floor_number), "false_val", fact.topic) % len(false_values)
        false_val = false_values[idx]
    else:
        # Fallback: just negate
        false_val = "something else"

    return f"My {fact.display_topic} is {false_val}."
