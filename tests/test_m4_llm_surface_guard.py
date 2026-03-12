"""M4 guardrail smoke: local model surface fallback on leak."""

import pytest

from textmystery.engine.llm_surface import apply_surface_guard


pytestmark = [pytest.mark.ts_leak, pytest.mark.milestone_m4]


def test_llm_surface_guard_falls_back_on_unauthorized_entity():
    result = apply_surface_guard(
        fallback_text="I don't know.",
        allowed_entities={"NICK", "NADIA"},
        use_model=True,
        model_fn=lambda _: "Victor did it.",
    )
    assert result.text == "I don't know."
    assert result.leaked is True


def test_llm_surface_guard_accepts_allowed_entities():
    result = apply_surface_guard(
        fallback_text="I don't know.",
        allowed_entities={"NICK", "NADIA"},
        use_model=True,
        model_fn=lambda _: "Nadia saw Nick.",
    )
    assert result.text == "Nadia saw Nick."
    assert result.leaked is False
