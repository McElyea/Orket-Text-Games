from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .types import CompanionMemory, RunHeader, WorldGraph


def load_companion_memory(path: str | Path) -> CompanionMemory:
    """Load persistent companion memory from disk.

    Missing file returns default memory for deterministic cold-start behavior.
    """
    file_path = Path(path)
    if not file_path.exists():
        return CompanionMemory()
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return CompanionMemory()
    return CompanionMemory(
        temperament=str(payload.get("temperament", "nice")),
        hint_threshold=int(payload.get("hint_threshold", 3)),
        voice_id=str(payload.get("voice_id", "default")),
        sessions_count=int(payload.get("sessions_count", 0)),
        last_played_at=payload.get("last_played_at"),
        stats=payload.get("stats") if isinstance(payload.get("stats"), dict) else {},
    )


def save_companion_memory(path: str | Path, memory: CompanionMemory) -> None:
    """Save persistent companion memory to disk."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(memory)
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def save_run_artifact(path: str | Path, artifact: dict[str, Any]) -> None:
    """Persist run artifact bundles for replay/debug (`world_graph`, transcript, reveal, header)."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(_jsonable(artifact), indent=2, sort_keys=True), encoding="utf-8")


def load_run_artifact(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def canonical_world_digest(world: WorldGraph) -> str:
    payload = {
        "scene_template_id": world.scene_template_id,
        "selected_npc_ids": list(world.selected_npc_ids),
        "culprit_npc_id": world.culprit_npc_id,
        "primary_crime_id": world.primary_crime_id,
        "facts": {k: {"fact_id": v.fact_id, "fact_type": v.fact_type, "value": v.value} for k, v in sorted(world.facts.items())},
        "npc_knowledge": {k: sorted(v) for k, v in sorted(world.npc_knowledge.items())},
        "npc_guards": {k: sorted(v) for k, v in sorted(world.npc_guards.items())},
        "npc_secrets": dict(sorted(world.npc_secrets.items())),
        "access_graph": {k: list(v) for k, v in sorted(world.access_graph.items())},
        "lead_unlocks": {k: list(v) for k, v in sorted(world.lead_unlocks.items())},
        "time_anchors": list(world.time_anchors),
        "access_anchors": list(world.access_anchors),
        "linkage_anchors": list(world.linkage_anchors),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_content_version(content_bundle: dict[str, Any]) -> str:
    encoded = json.dumps(content_bundle, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_resume_header(
    *,
    header: RunHeader,
    current_content_version: str,
    current_generator_version: str,
    compat_generator_versions: set[str] | None = None,
) -> tuple[bool, str | None]:
    compat = compat_generator_versions or {current_generator_version}
    if header.content_version != current_content_version:
        return (False, "content_version_mismatch")
    if header.generator_version not in compat:
        return (False, "generator_version_mismatch")
    return (True, None)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, set):
        return sorted(_jsonable(v) for v in value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value
