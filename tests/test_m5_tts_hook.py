"""M5 TTS hook smoke."""

import pytest

from textmystery.engine.tts import NoopVoiceProvider, boot_ritual_lines


pytestmark = [pytest.mark.milestone_m5]


def test_tts_boot_ritual_sequence():
    lines = boot_ritual_lines()
    assert len(lines) >= 4
    assert lines[0][0].lower() == "hello"


def test_noop_voice_provider_records_output():
    sink: list[str] = []
    voice = NoopVoiceProvider(sink=sink)
    voice.speak("hello", "default", "echo_wet")
    assert sink
    assert "hello" in sink[0]
