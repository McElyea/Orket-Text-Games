from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def live_mode_enabled() -> bool:
    return str(os.getenv("TEXTMYSTERY_RUN_LIVE", "")).strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def orket_base_url(live_mode_enabled: bool) -> str:
    if not live_mode_enabled:
        pytest.skip("Live integration disabled. Set TEXTMYSTERY_RUN_LIVE=1 to enable tests_integration.")
    url = str(os.getenv("TEXTMYSTERY_ORKET_BASE_URL", "")).strip()
    if not url:
        pytest.skip("Live integration enabled but TEXTMYSTERY_ORKET_BASE_URL is unset.")
    return url
