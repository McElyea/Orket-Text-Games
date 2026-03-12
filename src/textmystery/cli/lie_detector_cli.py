"""The Lie Detector -- CLI game loop.

20 questions with a twist: interview characters, deduce their truth policy,
judge their statement. Climb the tower to escape.

No dependency on TextMystery's mystery world graph.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from textmystery.engine.ansi_renderer import AnsiScreenRenderer
from textmystery.engine.lie_detector import (
    FloorNpc,
    FloorState,
    GameOutcome,
    InterviewTurn,
    LieDetectorState,
    PowerUpKind,
    generate_floors,
    judge_statement,
)
from textmystery.engine.persona import (
    PersonaArchetype,
    classify_topic,
    generate_personas,
    load_archetypes,
    resolve_persona_answer,
)
from textmystery.engine.persona_prompt import build_persona_prompt
from textmystery.engine.truth_policy import should_be_truthful

try:
    from orket_extension_sdk.tui import NullScreenRenderer, Panel
except ImportError:
    from textmystery.engine.ansi_renderer import AnsiScreenRenderer as _Fallback  # noqa: F811

    class NullScreenRenderer:  # type: ignore[no-redef]
        def render(self, panels):
            for p in panels:
                if p.title:
                    print(f"--- {p.title} ---")
                print(p.content)
                print()
        def clear(self):
            pass
        def size(self):
            return type("TS", (), {"columns": 80, "rows": 24})()

    class Panel:  # type: ignore[no-redef]
        def __init__(self, title="", content="", width=0):
            self.title = title
            self.content = content
            self.width = width


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parents[3] / "content" / "lie_detector.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _init_llm_provider(model: str):
    try:
        from textmystery.engine.ollama_llm import OllamaLLMProvider
        provider = OllamaLLMProvider(model=model)
        if provider.is_available():
            return provider
    except Exception:
        pass
    return None


def _build_tower_content(state: LieDetectorState) -> str:
    lines = []
    lines.append("  * ESCAPE *")
    lines.append("  " + "-" * 14)
    for f in range(state.total_floors, 0, -1):
        marker = "  <-- YOU" if f == state.current_floor else ""
        lines.append(f"  Floor {f}{marker}")
    lines.append("  " + "-" * 14)
    lines.append("  vvv SPIKES vvv")
    return "\n".join(lines)


def _build_status_line(state: LieDetectorState) -> str:
    parts = [f"Streak: {state.streak}"]
    if state.power_ups:
        counts: dict[str, int] = {}
        for p in state.power_ups:
            counts[p.value] = counts.get(p.value, 0) + 1
        items = [f"{k}x{v}" for k, v in counts.items()]
        parts.append("Power-ups: " + ", ".join(items))
    return "  " + "  |  ".join(parts)


def _build_interview_content(floor: FloorState, status: str) -> str:
    lines = []
    lines.append(f"  {floor.npc.display_name}  [Q {floor.questions_asked}/{floor.max_questions}]")
    lines.append(f"  Policy: ???  |  {status}")
    lines.append("")
    for turn in floor.interview_log[-4:]:
        lines.append(f"  You: {turn.raw_question}")
        lines.append(f"  {floor.npc.display_name}: {turn.response_text}")
        lines.append("")
    if not floor.statement_issued:
        remaining = floor.max_questions - floor.questions_asked
        if remaining > 0:
            lines.append(f"  > Ask a question ({remaining} left) or [J]udge")
        else:
            lines.append("  > No questions left. Press [J] to see the statement.")
    else:
        lines.append(f'  Statement: "{floor.npc.statement_text}"')
        lines.append("")
        lines.append("  > [T]rue or [F]alse?")
    return "\n".join(lines)


def _render_screen(renderer, state: LieDetectorState, floor: FloorState | None) -> None:
    renderer.clear()
    panels = [Panel(title="THE LIE DETECTOR", content=_build_tower_content(state))]
    if floor is not None:
        status = _build_status_line(state)
        panels.append(Panel(title="Interview", content=_build_interview_content(floor, status)))
    renderer.render(panels)


def _ask_persona(
    llm_provider,
    floor: FloorState,
    archetype: PersonaArchetype | None,
    raw_question: str,
    question_index: int,
) -> tuple[str, str]:
    """Ask the persona a question. Returns (response_text, topic)."""
    persona = floor.npc.persona
    policy = floor.npc.policy

    topic = classify_topic(raw_question)
    must_lie = not should_be_truthful(policy, question_index, topic)

    # Find matching fact
    fact = None
    for f in persona.facts:
        if f.topic == topic:
            fact = f
            break

    # Template response (always computed as fallback)
    template_text = resolve_persona_answer(
        persona, topic, must_lie, question_index, archetype,
    )

    # If LLM is available, try LLM rendering
    if llm_provider is not None:
        prompt_pack = build_persona_prompt(
            persona=persona,
            archetype=archetype,
            topic=topic,
            fact=fact,
            raw_question=raw_question,
            must_lie=must_lie,
        )
        try:
            from orket_extension_sdk.llm import GenerateRequest
            request = GenerateRequest(
                system_prompt=prompt_pack.system_prompt,
                user_message=prompt_pack.user_message,
                max_tokens=64,
                temperature=0.7,
            )
            response = llm_provider.generate(request)
            text = response.text.strip().strip('"').strip("'")
            if text:
                return text, topic
        except Exception:
            pass

    return template_text, topic


def _play(args) -> int:
    config = _load_config()
    total_floors = config.get("floors", 7)
    max_questions = config.get("max_questions_per_floor", 5)

    # Renderer
    if args.plain:
        renderer = NullScreenRenderer()
    else:
        renderer = AnsiScreenRenderer()

    # LLM
    llm_provider = None
    if not args.no_llm:
        llm_provider = _init_llm_provider(args.llm_model)

    llm_status = f"[llm] {args.llm_model} ready" if llm_provider else "[llm] off (template mode)"
    print(llm_status)

    # Generate personas
    personas = generate_personas(seed=args.seed, count=12)
    archetypes = load_archetypes()

    # Get policy sequence from config
    difficulty = config.get("difficulty", {}).get("normal", {})
    policy_seq = difficulty.get("floor_policies")

    # Generate floors
    floor_npcs = generate_floors(
        seed=args.seed,
        personas=personas,
        total_floors=total_floors,
        policy_sequence=policy_seq,
    )

    state = LieDetectorState(current_floor=1, total_floors=total_floors)

    print()
    print("=== THE LIE DETECTOR ===")
    print(f"Escape the tower! {total_floors} floors between you and freedom.")
    print("Interview characters, deduce their truth policy, judge their statement.")
    print("Correct = climb. Wrong = fall. Hit the spikes = game over.")
    print()
    input("Press Enter to begin...")

    floor_index = 0
    while state.outcome == GameOutcome.IN_PROGRESS:
        if floor_index >= len(floor_npcs):
            floor_index = floor_index % len(floor_npcs)
        npc = floor_npcs[floor_index]

        archetype = archetypes.get(npc.persona.archetype_id)

        floor = FloorState(
            floor_number=state.current_floor,
            npc=npc,
            max_questions=max_questions,
        )

        while not floor.judged:
            _render_screen(renderer, state, floor)

            if floor.statement_issued:
                line = input("  Judge> ").strip().upper()
                if line in ("T", "TRUE"):
                    player_says_true = True
                elif line in ("F", "FALSE"):
                    player_says_true = False
                else:
                    continue

                correct, delta = judge_statement(state, floor, player_says_true)

                renderer.clear()
                if correct:
                    msg = "CORRECT!"
                    if abs(delta) == 2:
                        msg += " Early solve bonus -- climb 2 floors!"
                    elif delta == 1:
                        msg += " Climb 1 floor."
                else:
                    msg = "WRONG! Fall 1 floor."

                truth_label = "TRUE" if npc.statement_is_true else "FALSE"
                renderer.render([
                    Panel(title="RESULT", content=f"  {msg}\n\n  The statement was {truth_label}.\n  Policy: {npc.policy.kind.value}"),
                    Panel(title="THE LIE DETECTOR", content=_build_tower_content(state)),
                ])

                if state.outcome != GameOutcome.IN_PROGRESS:
                    break

                if correct and state.streak > 0 and state.streak % 3 == 0:
                    print(f"\n  Streak of {state.streak}! Earned: OATH STONE")

                input("\n  Press Enter to continue...")
                continue

            # Question phase
            line = input("  Ask> ").strip()
            if not line:
                continue

            lower = line.lower()
            if lower in ("j", "judge"):
                floor.statement_issued = True
                continue
            if lower in ("q", "quit", "exit"):
                return 0
            if lower == "help":
                print("\n  Commands: type a question, [J]udge, [Q]uit")
                print("  Power-ups: [O]ath Stone, [R]eveal")
                input("  Press Enter...")
                continue

            if lower in ("o", "oath", "oath stone") and PowerUpKind.OATH_STONE in state.power_ups:
                state.power_ups.remove(PowerUpKind.OATH_STONE)
                print("  Oath Stone activated! Next answer will be truthful.")
                continue

            if lower in ("r", "reveal") and PowerUpKind.REVEAL in state.power_ups:
                state.power_ups.remove(PowerUpKind.REVEAL)
                print(f"  Policy revealed: {npc.policy.kind.value}")
                input("  Press Enter...")
                continue

            if floor.questions_asked >= floor.max_questions:
                print("  No questions remaining. Press [J] to judge.")
                continue

            response, topic = _ask_persona(
                llm_provider=llm_provider,
                floor=floor,
                archetype=archetype,
                raw_question=line,
                question_index=floor.questions_asked,
            )

            must_lie_val = not should_be_truthful(npc.policy, floor.questions_asked, topic)

            floor.interview_log.append(InterviewTurn(
                question_index=floor.questions_asked,
                raw_question=line,
                response_text=response,
                topic=topic,
                must_lie=must_lie_val,
            ))
            floor.questions_asked += 1

        floor_index += 1

    # End screen
    renderer.clear()
    if state.outcome == GameOutcome.WIN:
        renderer.render([Panel(
            title="ESCAPE!",
            content="  You made it out!\n\n  Congratulations -- you've beaten The Lie Detector.\n\n  " + _build_status_line(state),
        )])
    else:
        renderer.render([Panel(
            title="GAME OVER",
            content="  You hit the spikes.\n\n  The tower wins this time.\n\n  Try again with a different seed!",
        )])

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="The Lie Detector -- 20 questions with a twist")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--floors", type=int, default=None)
    parser.add_argument("--plain", action="store_true", help="No ANSI rendering")
    parser.add_argument("--llm-model", default="llama3.1:8b")
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    return _play(args)


if __name__ == "__main__":
    sys.exit(main())
