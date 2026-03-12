"""TS-CONTENT-001: Content schema regex and referential integrity. Milestone: M1."""

import pytest

from textmystery.engine.content import ContentValidationError, validate_content_bundle

pytestmark = [pytest.mark.ts_content, pytest.mark.milestone_m1]


def _valid_bundle():
    return {
        "npcs": [{"id": "NICK_VALE", "refusal_style_id": "REF_STYLE_1"}],
        "scenes": [{"id": "SCENE_001", "crime_palette_ids": ["CRIME_001"]}],
        "crimes": [{"id": "CRIME_001"}],
        "secrets": [{"id": "SECRET_001"}],
        "guards": [{"id": "GUARD_001"}],
        "refusal_styles": [{"id": "REF_STYLE_1"}],
    }


def test_ts_content_001_valid_bundle_passes():
    validate_content_bundle(_valid_bundle())


def test_ts_content_001_invalid_id_fails():
    bundle = _valid_bundle()
    bundle["npcs"][0]["id"] = "nick-lowercase"
    with pytest.raises(ContentValidationError):
        validate_content_bundle(bundle)
