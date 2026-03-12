# Implementation Strategy

Primary domain: strategy

## Documentation Strategy
Keep docs tight by using one primary home and explicit cross-links:
- Engine-first logic and contracts -> `docs/engine`
- Rules/content/progression -> `docs/gameplay`
- Player-facing and trust/safety expectations -> `docs/user-considerations`
- Delivery planning and milestone slicing -> `docs/strategy`

A document may span domains, but must declare:
- primary domain
- related domains
- requirement IDs covered

Locked thread decisions for v1 are captured in `docs/strategy/thread-decisions-addendum.md` and should be treated as scope guardrails.

## Build Strategy (Ground-up)
Execution priority: playable momentum over content breadth.

1. Foundation (M0)
- CLI/TUI shell
- config loading
- seed + scene + NPC selection
- deterministic template-only stubs

2. Deterministic Core (M1)
- world graph generation and freeze
- accusation lock + reveal graph
- run artifact persistence
- unit/scaffold test contracts green (`tests/`)

3. Interrogation Gameplay (M2)
- question classifier
- answer resolver
- refusal/dont_know/truth pipeline
- archetype response renderer

4. Companion Presence (M3)
- persistent player-centric memory
- nudge logic from visible transcript
- temperament profiles

5. Optional Local Model Surface (M4)
- model as style surface only
- strict factual boundaries and fallback

6. Optional Voice Hook (M5)
- pluggable TTS
- boot ritual voice mode

7. Live Orket Integration Gates (M2-M4, required before demo freeze)
- add `tests_integration/` that executes TextMystery turn flow through Orket runtime boundaries
- mirror core unit contracts in live form (determinism, truth/refuse/dont_know correctness, no-leak, resume parity)
- require parity between scaffold outputs and live outputs for shared seed/config fixtures
- keep live tests separate from unit tests so local iteration remains fast while integration confidence stays explicit

## Quality Gates
- Determinism gate: identical outcomes for same seed/config.
- Truth gate: no response fact outside world graph.
- Leak gate: companion cannot reference hidden state.
- UX gate: accusation confirm + hard lock + reveal always.
- Live parity gate: integration tests through Orket must match unit/scaffold contract expectations for pinned fixtures.

## Suggested Next Working Docs
- `docs/engine/test-strategy.md`
- `docs/gameplay/worldgen-algorithm.md`
- `docs/user-considerations/interaction-copy-guidelines.md`
