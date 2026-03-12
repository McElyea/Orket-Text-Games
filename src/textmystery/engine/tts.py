from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import AudioHint

try:
    from orket_extension_sdk.audio import AudioClip, NullTTSProvider, TTSProvider
except ImportError:
    TTSProvider = None  # type: ignore[assignment,misc]
    AudioClip = None  # type: ignore[assignment,misc]
    NullTTSProvider = None  # type: ignore[assignment,misc]


@dataclass
class NoopVoiceProvider:
    """Legacy voice provider for boot ritual. Logs to sink if provided."""
    sink: list[str] | None = None

    def speak(self, text: str, voice_id: str, effects_profile: str) -> None:
        if self.sink is not None:
            self.sink.append(f"[{voice_id}:{effects_profile}] {text}")


@dataclass(frozen=True)
class SynthResult:
    """Result of TTS synthesis. Contains raw audio bytes or None if unavailable."""
    text: str
    voice_id: str
    emotion_hint: str
    audio_bytes: bytes
    sample_rate: int
    channels: int
    format: str


def synthesize_speech(
    text: str,
    audio_hint: AudioHint | None,
    tts_provider: Any = None,
) -> SynthResult | None:
    """Synthesize speech from text and audio hint using SDK TTSProvider.

    Returns None if:
    - audio_hint is None (no voice profile for this NPC)
    - SDK is not installed
    - TTS provider is not available
    - Synthesis fails
    """
    if audio_hint is None:
        return None
    if TTSProvider is None:
        return None
    if tts_provider is None:
        return None

    try:
        clip = tts_provider.synthesize(
            text=text,
            voice_id=audio_hint.voice_id,
            emotion_hint=audio_hint.emotion_hint,
            speed=audio_hint.speed,
        )
        if not clip.samples:
            return None
        return SynthResult(
            text=text,
            voice_id=audio_hint.voice_id,
            emotion_hint=audio_hint.emotion_hint,
            audio_bytes=clip.samples,
            sample_rate=clip.sample_rate,
            channels=clip.channels,
            format=clip.format,
        )
    except Exception:
        return None


def boot_ritual_lines() -> list[tuple[str, str]]:
    return [
        ("hello", "echo_wet"),
        ("hello", "echo_wet"),
        ("hello", "echo_wet"),
        ("Let's begin.", "dry"),
    ]
