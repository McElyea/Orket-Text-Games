from __future__ import annotations

import dataclasses
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDENS_ROOT = PROJECT_ROOT / "tests" / "_goldens"


def _to_primitive(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _to_primitive(dataclasses.asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_primitive(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_to_primitive(v) for v in value]
    if isinstance(value, set):
        return sorted(_to_primitive(v) for v in value)
    return value


def dump_json(value: Any) -> dict[str, Any] | list[Any] | str | int | float | bool | None:
    return _to_primitive(value)


def _golden_path(name: str) -> Path:
    return GOLDENS_ROOT / f"{name}.json"


def load_golden(name: str) -> Any:
    path = _golden_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Golden file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def assert_matches_golden(name: str, data: Any) -> None:
    path = _golden_path(name)
    normalized = dump_json(data)
    if os.getenv("UPDATE_GOLDENS", "").strip().lower() in {"1", "true", "yes", "on"}:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding="utf-8")
        return
    expected = load_golden(name)
    assert normalized == expected


@pytest.fixture()
def default_config() -> dict[str, Any]:
    return {
        "difficulty": "normal",
        "max_worldgen_attempts": 12,
        "theme_bias": {
            "corporate_satire": 0.45,
            "cultural_spectacle": 0.45,
            "other": 0.10,
        },
    }


@pytest.fixture()
def sample_scene_id() -> str:
    return "SCENE_001"


@pytest.fixture()
def sample_npc_ids() -> list[str]:
    return ["NICK", "NADIA", "VICTOR", "GABE"]
