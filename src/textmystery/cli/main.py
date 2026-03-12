from __future__ import annotations

import argparse
import time
import wave
import io
from pathlib import Path

import yaml

from textmystery.engine.classify import classify_question
from textmystery.engine.persist import load_companion_memory, save_companion_memory
from textmystery.engine.runtime import GameRuntime
from textmystery.engine.tts import NoopVoiceProvider, boot_ritual_lines
from textmystery.engine.types import AudioHint, CompanionMemory, IntentId, SurfaceId
from textmystery.engine.worldgen import generate_world


def _load_piper_model_map() -> dict[str, str]:
    """Load abstract voice_id -> Piper model name mapping from voices.yaml."""
    voices_path = Path(__file__).resolve().parents[3] / "content" / "voices.yaml"
    if not voices_path.exists():
        return {}
    with open(voices_path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("piper_models", {})


def _init_tts_engine() -> tuple[str, object | None]:
    """Try Piper first, fall back to pyttsx3. Returns (backend_name, engine_or_provider)."""
    try:
        from orket_extension_sdk.piper_tts import PiperTTSProvider
        provider = PiperTTSProvider()
        voices = provider.list_voices()
        if voices:
            return "piper", provider
    except Exception:
        pass

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.stop()
        return "pyttsx3", True
    except Exception:
        pass

    return "none", None


def _speak(backend: str, engine: object | None, text: str, audio_hint: AudioHint | None, piper_map: dict[str, str] | None = None) -> None:
    """Speak text using the best available TTS backend."""
    if engine is None or not text or not text.strip():
        return

    if backend == "piper":
        _speak_piper(engine, text, audio_hint, piper_map or {})
    elif backend == "pyttsx3":
        _speak_pyttsx3(text, audio_hint)


def _speak_piper(provider: object, text: str, audio_hint: AudioHint | None, piper_map: dict[str, str]) -> None:
    """Synthesize and play audio via Piper TTS."""
    try:
        voice_id = "en_US-lessac-medium"  # default
        speed = 1.0
        emotion = "neutral"
        if audio_hint:
            voice_id = piper_map.get(audio_hint.voice_id, audio_hint.voice_id)
            speed = audio_hint.speed
            emotion = audio_hint.emotion_hint

        clip = provider.synthesize(text=text, voice_id=voice_id, emotion_hint=emotion, speed=speed)
        if not clip.samples:
            return

        _play_pcm(clip.samples, clip.sample_rate, clip.channels)
    except Exception:
        pass


def _play_pcm(samples: bytes, sample_rate: int, channels: int) -> None:
    """Play raw PCM s16le audio using the simplest available method."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt16, channels=channels, rate=sample_rate, output=True)
        stream.write(samples)
        stream.stop_stream()
        stream.close()
        pa.terminate()
        return
    except Exception:
        pass

    # Fallback: write to temp wav and play with winsound (Windows only)
    try:
        import winsound
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples)
        winsound.PlaySound(buf.getvalue(), winsound.SND_MEMORY)
    except Exception:
        pass


def _speak_pyttsx3(text: str, audio_hint: AudioHint | None) -> None:
    """Speak text using pyttsx3. Creates a fresh engine each call to avoid Windows SAPI stalls."""
    try:
        import pyttsx3
        e = pyttsx3.init()
        rate = e.getProperty("rate") or 150
        if audio_hint:
            e.setProperty("rate", int(rate * audio_hint.speed))
        e.say(text)
        e.runAndWait()
        e.stop()
    except Exception:
        pass


def _init_llm_provider(model: str) -> object | None:
    """Try to initialize OllamaLLMProvider for NPC responses."""
    try:
        from textmystery.engine.ollama_llm import OllamaLLMProvider
        provider = OllamaLLMProvider(model=model)
        if provider.is_available():
            print(f"[llm] {model} ready via Ollama.")
            return provider
        print(f"[llm] Model {model} not available. Template-only mode.")
    except Exception:
        print("[llm] Ollama not available. Template-only mode.")
    return None


def _default_npcs() -> list[str]:
    return ["NICK_VALE", "NADIA_BLOOM", "VICTOR_SLATE", "GABE_ROURKE"]


def _phrasebook() -> tuple[str, ...]:
    return (
        "Where were you at 11:03?",
        "When did you last see the boardroom feed?",
        "Who had access to the service door?",
        "Did you move the audit drive?",
        "Who did you see near the service door?",
        "Who was with you when the alarm hit?",
        "What do you know about access?",
    )

def _angle_help() -> tuple[str, ...]:
    return (
        "/time <question>    force time angle",
        "/where <question>   force location angle",
        "/access <question>  force access angle",
        "/witness <question> force witness angle",
    )


def _print_intro(seed: int, scene: str, npcs: list[str]) -> None:
    print("=== TEXTMYSTERY ===")
    print(f"Seed {seed} | Scene {scene}")
    print("11:03 PM. The archive alarms hit live TV.")
    print("A boardroom feed was hijacked in plain sight.")
    print("Someone moved the audit drive before lockdown.")
    print("Suspects: " + ", ".join(npcs))
    print("Type `help` for controls.")


def _resolve_npc_choice(raw: str, npcs: list[str]) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(npcs):
            return npcs[idx]
    upper = text.upper()
    for npc in npcs:
        if upper in {npc.upper(), npc.split("_")[0].upper()}:
            return npc
    return None


def _print_reveal(verdict: dict[str, object]) -> None:
    outcome = str(verdict.get("outcome") or "lose")
    reveal = verdict.get("reveal")
    print("\n=== REVEAL ===")
    print(f"Outcome: {outcome.upper()}")
    if reveal is None:
        print("No reveal available.")
        return
    culprit = getattr(reveal, "culprit_npc_id", "unknown")
    print(f"Culprit: {culprit}")
    primary = getattr(reveal, "primary_crime_id", "unknown")
    print(f"Primary chain: {primary}")
    refusal_causes = getattr(reveal, "refusal_causes", {}) or {}
    if refusal_causes:
        print("Why refusals happened:")
        for key in sorted(refusal_causes.keys()):
            print(f"- {key} -> {refusal_causes[key]}")


def _play_interactive(runtime: GameRuntime, npcs: list[str], memory: CompanionMemory, tts_backend: str = "none", tts_engine: object | None = None, piper_map: dict[str, str] | None = None) -> None:
    def _print_help() -> None:
        print("Ask any free-text question.")
        print("Commands: back, accuse, help, quit")
        print("Try these exact prompts:")
        for line in _phrasebook():
            print(f"- {line}")
        print("Angle commands:")
        for line in _angle_help():
            print(f"- {line}")

    def _parse_angle(raw_line: str) -> tuple[SurfaceId | None, str]:
        text = str(raw_line or "").strip()
        mapping = {
            "/time": SurfaceId.SURF_TIME,
            "/where": SurfaceId.SURF_LOCATION,
            "/access": SurfaceId.SURF_ACCESS,
            "/witness": SurfaceId.SURF_WITNESS,
        }
        for prefix, surface in mapping.items():
            if not text.lower().startswith(prefix):
                continue
            rest = text[len(prefix) :].strip()
            return surface, rest
        return None, text

    def _resolve_angle_choice(choice: str) -> tuple[SurfaceId | None, str | None]:
        text = str(choice or "").strip()
        lowered = text.lower()
        simple_map = {
            "1": SurfaceId.SURF_TIME,
            "time": SurfaceId.SURF_TIME,
            "2": SurfaceId.SURF_LOCATION,
            "where": SurfaceId.SURF_LOCATION,
            "3": SurfaceId.SURF_ACCESS,
            "access": SurfaceId.SURF_ACCESS,
            "4": SurfaceId.SURF_WITNESS,
            "witness": SurfaceId.SURF_WITNESS,
        }
        if lowered in simple_map:
            return simple_map[lowered], None

        forced_surface, parsed = _parse_angle(text)
        if forced_surface is not None:
            question_override = parsed if parsed else text
            return forced_surface, question_override

        inferred = classify_question(text, npcs, {})
        if inferred.intent_id != IntentId.UNCLASSIFIED_AMBIGUOUS and inferred.surface_id in {
            SurfaceId.SURF_TIME,
            SurfaceId.SURF_LOCATION,
            SurfaceId.SURF_ACCESS,
            SurfaceId.SURF_WITNESS,
        }:
            return inferred.surface_id, text

        return None, None

    def _chat_with_suspect(npc_id: str) -> bool:
        print(f"\n--- Interrogating {npc_id} ---")
        print("Type your question, or `back` to return to suspects.")
        print("You can also use `accuse`, `help`, or `quit` here.")
        while True:
            line = input(f"{npc_id}> ").strip()
            lower_line = line.lower()
            if lower_line in {"back", "b"}:
                return False
            if lower_line in {"quit", "exit", "q"}:
                print("Exiting case.")
                return True
            if lower_line in {"help", "h", "?"}:
                _print_help()
                continue
            if lower_line == "accuse":
                accused_raw = input("Accuse who (1-4/name)? ").strip()
                accused = _resolve_npc_choice(accused_raw, npcs)
                if not accused:
                    print("Unknown suspect.")
                    continue
                confirm = input(f"Final accusation: {accused}. Type YES to confirm: ").strip()
                if confirm.lower() not in {"yes", "y"}:
                    print("Accusation cancelled.")
                    continue
                verdict = runtime.accuse(accused_npc_id=accused)
                _print_reveal(verdict)
                return True
            if not line:
                print("Empty question ignored.")
                continue
            forced_surface, question = _parse_angle(line)
            if forced_surface is not None and not question:
                print("Provide a question after the angle command.")
                continue
            turn = runtime.ask(
                npc_id=npc_id,
                raw_question=question,
                memory=memory,
                forced_surface=forced_surface,
            )
            canonical = turn["canonical_query"]
            print(
                f"(Angle: {canonical.surface_id.value.replace('SURF_', '')} | "
                f"Intent: {canonical.intent_id.value} | conf {canonical.confidence:.2f})"
            )
            print(f"{npc_id}: {turn['npc_response_text']}")
            _speak(tts_backend, tts_engine, turn['npc_response_text'], turn.get('audio_hint'), piper_map)
            if turn["companion_line"]:
                print(f"[companion] {turn['companion_line']}")

    while True:
        print("\nSuspects:")
        for index, npc in enumerate(npcs, start=1):
            print(f"{index}. {npc}")
        command = input("\nChoose suspect (1-4/name) or `accuse`/`help`/`quit`: ").strip()
        lower = command.lower()
        if lower in {"quit", "exit", "q"}:
            print("Exiting case.")
            return
        if lower in {"help", "h", "?"}:
            print("Ask flow: choose suspect -> type any question.")
            print("Accuse flow: type `accuse`, choose suspect, confirm yes/y.")
            print("Phrasebook:")
            for line in _phrasebook():
                print(f"- {line}")
            print("Angle commands:")
            for line in _angle_help():
                print(f"- {line}")
            continue
        if lower == "accuse":
            accused_raw = input("Accuse who (1-4/name)? ").strip()
            accused = _resolve_npc_choice(accused_raw, npcs)
            if not accused:
                print("Unknown suspect.")
                continue
            confirm = input(f"Final accusation: {accused}. Type YES to confirm: ").strip()
            if confirm.lower() not in {"yes", "y"}:
                print("Accusation cancelled.")
                continue
            verdict = runtime.accuse(accused_npc_id=accused)
            _print_reveal(verdict)
            return

        npc_id = _resolve_npc_choice(command, npcs)
        if not npc_id:
            print("Unknown suspect selection.")
            continue
        should_end = _chat_with_suspect(npc_id)
        if should_end:
            return


def main() -> int:
    parser = argparse.ArgumentParser(description="TextMystery local CLI")
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--scene", default="SCENE_001")
    parser.add_argument("--difficulty", default="normal", choices=["normal", "hard"])
    parser.add_argument("--memory-path", default="workspace/textmystery/companion_memory.json")
    parser.add_argument("--scripted-question", default=None)
    parser.add_argument("--accuse", default=None)
    parser.add_argument("--play", action="store_true", help="Start interactive play loop.")
    parser.add_argument("--llm-model", default="llama3.1:8b", help="Ollama model for NPC responses.")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM-backed NPC responses.")
    args = parser.parse_args()

    npcs = _default_npcs()
    memory_path = Path(args.memory_path)
    memory = load_companion_memory(memory_path)
    piper_map = _load_piper_model_map()
    tts_backend, tts_engine = _init_tts_engine()
    if tts_backend == "piper":
        print("[audio] Piper neural TTS ready.")
    elif tts_backend == "pyttsx3":
        print("[audio] pyttsx3 SAPI TTS ready (fallback).")
    else:
        print("[audio] No TTS engine available. Text-only mode.")

    llm_provider = None
    if not args.no_llm:
        llm_provider = _init_llm_provider(args.llm_model)

    world = generate_world(args.seed, args.scene, npcs, args.difficulty, config={})
    runtime = GameRuntime(world=world, settings={"hint_threshold": memory.hint_threshold}, llm_provider=llm_provider)

    if args.scripted_question:
        turn = runtime.ask(npc_id=npcs[0], raw_question=args.scripted_question, memory=memory)
        print(turn["npc_response_text"])
        _speak(tts_backend, tts_engine, turn["npc_response_text"], turn.get("audio_hint"), piper_map)
        if turn["companion_line"]:
            print(f"[companion] {turn['companion_line']}")

    if args.accuse:
        verdict = runtime.accuse(accused_npc_id=args.accuse)
        print(f"outcome={verdict['outcome']}")
        print(f"culprit={verdict['reveal'].culprit_npc_id}")

    if args.play or (not args.scripted_question and not args.accuse):
        _print_intro(seed=args.seed, scene=args.scene, npcs=npcs)
        _play_interactive(runtime=runtime, npcs=npcs, memory=memory, tts_backend=tts_backend, tts_engine=tts_engine, piper_map=piper_map)

    save_companion_memory(
        memory_path,
        memory.__class__(
            temperament=memory.temperament,
            hint_threshold=memory.hint_threshold,
            voice_id=memory.voice_id,
            sessions_count=memory.sessions_count + 1,
            last_played_at=int(time.time()),
            stats=memory.stats,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
