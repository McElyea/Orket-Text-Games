"""LLM prompt building for Lie Detector personas.

Standalone prompt construction — no dependency on mystery NPC prompt system.
"""
from __future__ import annotations

from dataclasses import dataclass

from .persona import Persona, PersonaArchetype, PersonaFact


@dataclass(frozen=True)
class PersonaPromptPack:
    """System + user prompt for LLM rendering."""

    system_prompt: str
    user_message: str
    max_words: int


def build_persona_prompt(
    *,
    persona: Persona,
    archetype: PersonaArchetype | None,
    topic: str,
    fact: PersonaFact | None,
    raw_question: str,
    must_lie: bool,
    rejection_reason: str | None = None,
) -> PersonaPromptPack:
    """Build LLM prompt for a persona response.

    Simple prompt construction that gives the LLM enough context to
    stay in character while answering truthfully or lying.
    """
    max_words = archetype.max_words if archetype else 14
    personality = archetype.description if archetype else "Neutral, conversational."

    lines = [
        f"You are {persona.display_name}, a character in a deduction game.",
        f"Personality: {personality}",
        persona.backstory,
        "",
        "Rules:",
        f"- Respond in {max_words} words or fewer.",
        "- Stay in character. One or two sentences only.",
        "- No quotation marks around your response.",
        "- Do not mention being a character, NPC, or AI.",
    ]

    # Mode instruction
    if fact is not None:
        if must_lie:
            lines.append("")
            lines.append(
                f'You are LYING. The truth is: "{fact.display_topic} is {fact.value}." '
                "Give a plausible but FALSE answer. Do NOT state the truth."
            )
        else:
            lines.append("")
            lines.append(
                f"You are answering truthfully. Your {fact.display_topic} is {fact.value}. "
                "Convey this naturally."
            )
    else:
        if must_lie:
            lines.append("")
            lines.append(
                "You don't know about this topic. Make something up — give a confident "
                "but fabricated answer."
            )
        else:
            lines.append("")
            lines.append(
                "You don't know about this topic. Say you're not sure or don't have "
                "an answer for that."
            )

    if rejection_reason:
        lines.append("")
        lines.append(
            f"IMPORTANT: Your previous response was rejected because: {rejection_reason}. "
            "Fix this in your new response."
        )

    system_prompt = "\n".join(lines)
    return PersonaPromptPack(
        system_prompt=system_prompt,
        user_message=raw_question,
        max_words=max_words,
    )
