from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import hashlib


try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


@dataclass(frozen=True)
class PromptRules:
    max_words: int = 14
    end_punctuation: str = "."
    allow_ellipsis: bool = False
    allow_exclamation: bool = False
    allow_questions: bool = True
    allow_contractions: bool = True


@dataclass(frozen=True)
class PromptBanks:
    refuse: Tuple[str, ...] = ()
    dont_know: Tuple[str, ...] = ()
    clarify: Tuple[str, ...] = ()
    nudge: Tuple[str, ...] = ()
    fact_format: Tuple[str, ...] = ("{fact}.",)


@dataclass(frozen=True)
class ArchetypePrompt:
    archetype_id: str
    description: str
    rules: PromptRules
    banks: PromptBanks


@dataclass(frozen=True)
class NpcPrompt:
    npc_id: str
    archetype_id: str
    display_name: str
    override_rules: Optional[PromptRules] = None
    override_banks: Optional[PromptBanks] = None


@dataclass(frozen=True)
class PromptConfig:
    version: int
    defaults: PromptRules
    archetypes: Dict[str, ArchetypePrompt]
    npcs: Dict[str, NpcPrompt]


@dataclass(frozen=True)
class PromptContext:
    npc_id: str
    scene_id: str
    turn_index: int
    mode: str
    fact: Optional[str] = None
    topic: Optional[str] = None


class PromptingError(RuntimeError):
    pass


def load_prompt_config(content_dir: Path) -> PromptConfig:
    if yaml is None:
        raise PromptingError("PyYAML is not available.")

    archetypes_path = content_dir / "prompts" / "archetypes.yaml"
    npcs_path = content_dir / "prompts" / "npcs.yaml"

    arche_raw = _load_yaml(archetypes_path)
    npcs_raw = _load_yaml(npcs_path)

    version = int(arche_raw.get("version", 1))
    defaults = _parse_rules(arche_raw.get("defaults", {}), fallback=PromptRules())

    archetypes: Dict[str, ArchetypePrompt] = {}
    for aid, aobj in (arche_raw.get("archetypes") or {}).items():
        desc = str(aobj.get("description", "")).strip()
        rules = _parse_rules(aobj.get("rules", {}), fallback=defaults)
        banks = _parse_banks(aobj.get("banks", {}))
        archetypes[aid] = ArchetypePrompt(aid, desc, rules, banks)

    npcs: Dict[str, NpcPrompt] = {}
    for nid, nobj in (npcs_raw.get("npcs") or {}).items():
        archetype_id = str(nobj.get("archetype", "")).strip()
        display_name = str(nobj.get("display_name", nid)).strip()
        overrides = nobj.get("overrides") or {}
        override_rules = _parse_rules(overrides.get("rules", {}), fallback=defaults) if "rules" in overrides else None
        override_banks = _parse_banks(overrides.get("banks", {})) if "banks" in overrides else None
        npcs[nid] = NpcPrompt(
            npc_id=nid,
            archetype_id=archetype_id,
            display_name=display_name,
            override_rules=override_rules,
            override_banks=override_banks,
        )

    return PromptConfig(version=version, defaults=defaults, archetypes=archetypes, npcs=npcs)


def resolve_prompt_pack(cfg: PromptConfig, npc_id: str) -> Tuple[PromptRules, PromptBanks]:
    npc = cfg.npcs.get(npc_id)
    if npc is None:
        return cfg.defaults, PromptBanks(
            refuse=("I can't answer that.",),
            dont_know=("I don't know.",),
            clarify=("Be specific.",),
            nudge=("Ask about time or access.",),
            fact_format=("{fact}.",),
        )

    arche = cfg.archetypes.get(npc.archetype_id)
    if arche is None:
        return cfg.defaults, PromptBanks(
            refuse=("I can't answer that.",),
            dont_know=("I don't know.",),
            clarify=("Be specific.",),
            nudge=("Ask about time or access.",),
            fact_format=("{fact}.",),
        )

    rules = npc.override_rules or arche.rules
    banks = _merge_banks(arche.banks, npc.override_banks)
    return rules, banks


def render_text(cfg: PromptConfig, ctx: PromptContext) -> str:
    rules, banks = resolve_prompt_pack(cfg, ctx.npc_id)
    mode = ctx.mode.strip().upper()

    if mode == "REFUSE":
        return _postprocess(_pick(banks.refuse, ctx), rules, ctx)
    if mode == "DONT_KNOW":
        return _postprocess(_pick(banks.dont_know, ctx), rules, ctx)
    if mode == "CLARIFY":
        return _postprocess(_pick(banks.clarify, ctx), rules, ctx)
    if mode == "NUDGE":
        return _postprocess(_pick(banks.nudge, ctx), rules, ctx)
    if mode == "FACT":
        if not ctx.fact:
            return _postprocess(_pick(banks.dont_know or ("I don't know.",), ctx), rules, ctx)
        return _postprocess(_pick(banks.fact_format, ctx), rules, ctx)
    return "I don't know."


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise PromptingError(f"Missing prompt file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        obj = yaml.safe_load(handle) or {}
    if not isinstance(obj, dict):
        raise PromptingError(f"Invalid YAML root: {path}")
    return obj


def _parse_rules(raw: Dict[str, Any], fallback: PromptRules) -> PromptRules:
    if not isinstance(raw, dict):
        return fallback
    return PromptRules(
        max_words=int(raw.get("max_words", fallback.max_words)),
        end_punctuation=str(raw.get("end_punctuation", fallback.end_punctuation)),
        allow_ellipsis=bool(raw.get("allow_ellipsis", fallback.allow_ellipsis)),
        allow_exclamation=bool(raw.get("allow_exclamation", fallback.allow_exclamation)),
        allow_questions=bool(raw.get("allow_questions", fallback.allow_questions)),
        allow_contractions=bool(raw.get("allow_contractions", fallback.allow_contractions)),
    )


def _parse_banks(raw: Dict[str, Any]) -> PromptBanks:
    if not isinstance(raw, dict):
        return PromptBanks()

    def as_tuple(key: str, default: Tuple[str, ...] = ()) -> Tuple[str, ...]:
        val = raw.get(key)
        if val is None:
            return default
        if isinstance(val, str):
            return (val,)
        if isinstance(val, list):
            out: List[str] = []
            for item in val:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
            return tuple(out)
        return default

    return PromptBanks(
        refuse=as_tuple("refuse"),
        dont_know=as_tuple("dont_know"),
        clarify=as_tuple("clarify"),
        nudge=as_tuple("nudge"),
        fact_format=as_tuple("fact_format", default=("{fact}.",)),
    )


def _merge_banks(base: PromptBanks, override: Optional[PromptBanks]) -> PromptBanks:
    if override is None:
        return base
    return PromptBanks(
        refuse=override.refuse or base.refuse,
        dont_know=override.dont_know or base.dont_know,
        clarify=override.clarify or base.clarify,
        nudge=override.nudge or base.nudge,
        fact_format=override.fact_format or base.fact_format,
    )


def _pick(options: Sequence[str], ctx: PromptContext) -> str:
    if not options:
        return "I don't know."
    idx = _stable_index(len(options), ctx)
    return options[idx]


def _stable_index(n: int, ctx: PromptContext) -> int:
    h = hashlib.sha256()
    parts = [ctx.scene_id, str(ctx.turn_index), ctx.npc_id, ctx.mode, ctx.fact or "", ctx.topic or ""]
    h.update(("|".join(parts)).encode("utf-8"))
    val = int.from_bytes(h.digest()[:8], "big", signed=False)
    return val % n


def _postprocess(template: str, rules: PromptRules, ctx: PromptContext) -> str:
    text = template
    text = text.replace("{fact}", (ctx.fact or "").strip()) if "{fact}" in text else text
    text = text.replace("{topic}", (ctx.topic or "").strip()) if "{topic}" in text else text
    text = text.strip()
    if not text:
        return "..."

    text = _apply_word_limit(text, rules.max_words)
    if not rules.allow_ellipsis and "..." in text:
        text = text.replace("...", ".")
    if not rules.allow_exclamation:
        text = text.replace("!", ".")
    if not rules.allow_questions and "?" in text:
        text = text.replace("?", rules.end_punctuation)

    if text and text[-1].isalnum():
        text = text + (rules.end_punctuation or ".")
    return text


def _apply_word_limit(text: str, max_words: int) -> str:
    if max_words <= 0:
        return text
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip() + "..."
