from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from typing import Any

from textmystery.engine.persist import canonical_world_digest
from textmystery.engine.runtime import GameRuntime
from textmystery.engine.types import CompanionMemory
from textmystery.engine.worldgen import generate_world
from textmystery.engine.reveal import compute_reveal


def _normalize(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _normalize(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, set):
        return sorted(_normalize(v) for v in value)
    return value


def _digest_payload(payload: Any) -> str:
    normalized = _normalize(payload)
    encoded = json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _serialize_audio_hint(hint: Any) -> dict[str, Any] | None:
    if hint is None:
        return None
    return {
        "voice_id": str(getattr(hint, "voice_id", "default")),
        "emotion_hint": str(getattr(hint, "emotion_hint", "neutral")),
        "speed": float(getattr(hint, "speed", 1.0)),
    }


def parity_check(request_payload: dict[str, Any]) -> dict[str, Any]:
    run_header = request_payload.get("run_header") if isinstance(request_payload.get("run_header"), dict) else {}
    transcript_inputs = request_payload.get("transcript_inputs")
    if not isinstance(transcript_inputs, list):
        transcript_inputs = []

    seed = int(run_header.get("seed", 12345))
    scene_id = str(run_header.get("scene_id", "SCENE_001"))
    npc_ids = run_header.get("npc_ids") if isinstance(run_header.get("npc_ids"), list) else []
    npc_ids = [str(n) for n in npc_ids] or ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"]
    difficulty = str(run_header.get("difficulty", "normal")).strip().lower() or "normal"

    tts_provider = request_payload.get("tts_provider")

    world = generate_world(seed, scene_id, npc_ids, difficulty, config={})
    runtime = GameRuntime(world=world, settings={"hint_threshold": 3}, tts_provider=tts_provider)
    memory = CompanionMemory()

    turn_results: list[dict[str, Any]] = []
    accusation_result: dict[str, Any] | None = None

    for item in transcript_inputs:
        if not isinstance(item, dict):
            continue
        turn_idx = int(item.get("turn", len(turn_results) + 1))
        accuse_block = item.get("accuse") if isinstance(item.get("accuse"), dict) else None
        if accuse_block is not None:
            accused_npc_id = str(accuse_block.get("npc_id", "")).strip()
            verdict = runtime.accuse(accused_npc_id=accused_npc_id)
            reveal = compute_reveal(world, accused_npc_id=accused_npc_id)
            accusation_result = {
                "accused_npc_id": accused_npc_id,
                "outcome": "WIN" if verdict.get("outcome") == "win" else "LOSE",
                "reveal_digest": _digest_payload(reveal),
            }
            continue

        npc_id = str(item.get("npc_id", "")).strip() or npc_ids[0]
        raw_question = str(item.get("raw_question", "")).strip()
        turn = runtime.ask(npc_id=npc_id, raw_question=raw_question, memory=memory)
        cq = turn["canonical_query"]
        decision = turn["decision"]
        turn_results.append(
            {
                "turn": turn_idx,
                "canonical_query": {
                    "intent_id": cq.intent_id.value,
                    "surface_id": cq.surface_id.value,
                    "confidence": cq.confidence,
                    "raw_text_hash": cq.raw_text_hash,
                },
                "decision": decision.mode.value,
                "fact_id": decision.fact_id,
                "npc_response_text": turn["npc_response_text"],
                "companion_line": turn["companion_line"],
                "audio_hint": _serialize_audio_hint(turn.get("audio_hint")),
                "has_audio": turn.get("synth_result") is not None,
            }
        )

    if accusation_result is None:
        accusation_result = {
            "accused_npc_id": None,
            "outcome": "LOSE",
            "reveal_digest": _digest_payload(compute_reveal(world, accused_npc_id="")),
        }

    return {
        "world_digest": canonical_world_digest(world),
        "turn_results": turn_results,
        "accusation_result": accusation_result,
    }


def leak_check(request_payload: dict[str, Any]) -> dict[str, Any]:
    allowed_entities = request_payload.get("allowed_entities") if isinstance(request_payload.get("allowed_entities"), list) else []
    allowed_fact_values = (
        request_payload.get("allowed_fact_values") if isinstance(request_payload.get("allowed_fact_values"), list) else []
    )
    text = str(request_payload.get("text", ""))

    allow_entity_upper = {str(v).upper() for v in allowed_entities}
    allow_fact = {str(v) for v in allowed_fact_values}

    violations: list[dict[str, Any]] = []

    # Entity leak detection is ID-oriented in v1 (e.g., NICK_VALE, PANEL).
    for match in re.finditer(r"\b[A-Z0-9_]{3,}\b", text):
        token = match.group(0)
        if token.upper() not in allow_entity_upper:
            violations.append(
                {
                    "type": "NEW_ENTITY",
                    "span": {"start": match.start(), "end": match.end()},
                    "token": token,
                }
            )

    for match in re.finditer(r"\b\d{1,2}:\d{2}\b", text):
        token = match.group(0)
        if token not in allow_fact:
            violations.append(
                {
                    "type": "NEW_FACT_VALUE",
                    "span": {"start": match.start(), "end": match.end()},
                    "token": token,
                }
            )

    for pattern in ("culprit", "guard reason", "secret id"):
        idx = text.lower().find(pattern)
        if idx >= 0:
            violations.append(
                {
                    "type": "DISALLOWED_PATTERN",
                    "span": {"start": idx, "end": idx + len(pattern)},
                    "token": text[idx : idx + len(pattern)],
                }
            )

    return {
        "ok": len(violations) == 0,
        "violations": violations,
    }
