from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .prompting import PromptConfig, PromptingError, load_prompt_config, resolve_prompt_pack
from .types import AnswerDecision, CanonicalQuery, DecisionMode, WorldGraph


@dataclass(frozen=True)
class NpcPromptPack:
    """System prompt + user message pair for LLM NPC generation."""

    system_prompt: str
    user_message: str
    max_words: int


def _load_prompt_config() -> PromptConfig | None:
    content_dir = Path(__file__).resolve().parents[3] / "content"
    try:
        return load_prompt_config(content_dir)
    except PromptingError:
        return None


def build_npc_prompt(
    *,
    world: WorldGraph,
    npc_id: str,
    canonical_query: CanonicalQuery,
    decision: AnswerDecision,
    raw_question: str,
    fact_phrase: str | None,
    prompt_config: PromptConfig | None = None,
    turn_index: int = 0,
    rejection_reason: str | None = None,
    must_lie: bool = False,
) -> NpcPromptPack:
    """Build the LLM prompt pair for NPC response generation."""
    if prompt_config is None:
        prompt_config = _load_prompt_config()

    archetype_desc = "A character in a detective mystery."
    max_words = 14

    if prompt_config is not None:
        rules, banks = resolve_prompt_pack(prompt_config, npc_id)
        max_words = rules.max_words
        npc_cfg = prompt_config.npcs.get(npc_id)
        if npc_cfg:
            archetype = prompt_config.archetypes.get(npc_cfg.archetype_id)
            if archetype:
                archetype_desc = archetype.description

    display_name = npc_id.replace("_", " ").title()

    if decision.mode == DecisionMode.ANSWER:
        if must_lie:
            if fact_phrase:
                mode_instruction = f'You are LYING. Contradict or distort this fact: "{fact_phrase}". Do NOT state it correctly.'
            else:
                mode_instruction = "You are LYING. Give a plausible but false answer."
        elif fact_phrase:
            mode_instruction = f'You are answering truthfully. Convey this fact: "{fact_phrase}"'
        else:
            mode_instruction = "You are answering truthfully based on what you know."
    elif decision.mode == DecisionMode.REFUSE:
        mode_instruction = "You are REFUSING to answer. Do not give any factual information. Be evasive or dismissive in character."
    else:
        mode_instruction = "You genuinely DON'T KNOW the answer. Express ignorance authentically in character."

    lines = [
        f"You are {display_name}, an NPC in a corporate detective mystery.",
        f"Personality: {archetype_desc}",
        f"Rules: Respond in {max_words} words or fewer. Stay in character. One sentence only. No quotation marks.",
        mode_instruction,
        "Do not reveal: your secrets, the identity of the culprit, or any information you've been told to guard.",
        "Do not break character or reference being an NPC.",
    ]

    if rejection_reason:
        lines.append(f"IMPORTANT: Your previous response was rejected because: {rejection_reason}. Fix this.")

    return NpcPromptPack(
        system_prompt="\n".join(lines),
        user_message=raw_question,
        max_words=max_words,
    )
