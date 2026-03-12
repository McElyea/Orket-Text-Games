from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SurfaceGuardResult:
    text: str
    leaked: bool


def apply_surface_guard(
    *,
    fallback_text: str,
    allowed_entities: set[str],
    use_model: bool,
    model_fn: Callable[[str], str] | None = None,
) -> SurfaceGuardResult:
    if not use_model or model_fn is None:
        return SurfaceGuardResult(text=fallback_text, leaked=False)

    candidate = str(model_fn(fallback_text) or "").strip()
    if not candidate:
        return SurfaceGuardResult(text=fallback_text, leaked=False)

    entities = set(re.findall(r"\b[A-Z][a-zA-Z0-9_]+\b", candidate))
    allow_upper = {str(e).upper() for e in allowed_entities}
    unauthorized = {e for e in entities if e.upper() not in allow_upper}
    if unauthorized:
        return SurfaceGuardResult(text=fallback_text, leaked=True)
    return SurfaceGuardResult(text=candidate, leaked=False)
