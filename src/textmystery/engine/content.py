from __future__ import annotations

import re
from typing import Any

ID_PATTERN = re.compile(r"^[A-Z0-9_]+$")


class ContentValidationError(ValueError):
    pass


def validate_id(value: str, *, field_name: str) -> None:
    if not ID_PATTERN.match(value):
        raise ContentValidationError(f"invalid {field_name} '{value}' (must match ^[A-Z0-9_]+$)")


def validate_content_bundle(bundle: dict[str, Any]) -> None:
    """Validate minimal referential integrity and ID formats for v1 content bundles."""
    required_keys = {"npcs", "scenes", "crimes", "secrets", "guards", "refusal_styles"}
    missing = sorted(key for key in required_keys if key not in bundle)
    if missing:
        raise ContentValidationError(f"missing required content sections: {', '.join(missing)}")

    for section in required_keys:
        rows = bundle.get(section)
        if not isinstance(rows, list):
            raise ContentValidationError(f"section '{section}' must be a list")

    id_fields = {
        "npcs": "id",
        "scenes": "id",
        "crimes": "id",
        "secrets": "id",
        "guards": "id",
        "refusal_styles": "id",
    }
    seen_by_section: dict[str, set[str]] = {k: set() for k in id_fields}
    for section, id_field in id_fields.items():
        for row in bundle[section]:
            if not isinstance(row, dict):
                raise ContentValidationError(f"section '{section}' contains non-object row")
            raw_id = str(row.get(id_field) or "").strip()
            if not raw_id:
                raise ContentValidationError(f"section '{section}' contains row without '{id_field}'")
            validate_id(raw_id, field_name=f"{section}.{id_field}")
            if raw_id in seen_by_section[section]:
                raise ContentValidationError(f"duplicate id '{raw_id}' in section '{section}'")
            seen_by_section[section].add(raw_id)

    refusal_style_ids = seen_by_section["refusal_styles"]
    for npc in bundle["npcs"]:
        ref = str(npc.get("refusal_style_id") or "").strip()
        if ref and ref not in refusal_style_ids:
            raise ContentValidationError(f"npc references unknown refusal_style_id '{ref}'")

    crime_ids = seen_by_section["crimes"]
    for scene in bundle["scenes"]:
        palette = scene.get("crime_palette_ids")
        if palette is None:
            continue
        if not isinstance(palette, list):
            raise ContentValidationError("scene.crime_palette_ids must be list")
        for crime_id in palette:
            cid = str(crime_id or "").strip()
            validate_id(cid, field_name="scenes.crime_palette_ids")
            if cid not in crime_ids:
                raise ContentValidationError(f"scene references unknown crime id '{cid}'")
