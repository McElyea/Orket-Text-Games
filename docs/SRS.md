# Software Requirements Specification (SRS)

Project: TextMystery (Orket extension toy game)
Version: v1 draft
Scope: local-only, text-first detective experience

## 1. Product Intent
TextMystery is a deterministic detective game that demonstrates controlled local AI behavior on Orket. The player interrogates NPCs using free text and makes one hard accusation. The run ends with full reveal regardless of win/lose.
This is a toy/demo project intended to ship quickly for local play sessions with friends. Momentum and a playable loop are prioritized over content breadth.

## 2. Goals
- 10-20 minute solvable runs.
- Typical exchange budget of 8-15 meaningful interrogations.
- One primary crime per run.
- NPC truth policy: truthful, refusal, or don't know.
- Companion presence without hidden-knowledge leaks.
- Deterministic replay by seed + config.

## 3. Non-goals
- No glitch/carryover NPC memory in v1.
- No in-run direct companion chat channel in v1.
- No speculative/partial facts.
- No animation/3D.

## 4. System Context
- Client: terminal/TUI or minimal web text UI.
- Game Orchestrator: local process boundary for world generation and turn handling.
- Orket: deterministic workflow execution, state transitions, artifact persistence, replayability.

## 5. Functional Requirements

### 5.1 Engine and Orket
- `TM-ENG-001`: System shall generate a frozen `WorldGraph` at run start before first turn.
- `TM-ENG-002`: System shall execute turn pipeline deterministically: classify -> resolve -> render -> optional nudge -> append transcript.
- `TM-ENG-003`: Accusation shall be single-shot and lock further questioning.
- `TM-ENG-004`: System shall emit `RevealGraph` after accusation for both win and lose.
- `TM-ENG-005`: Companion memory persistence shall exclude hidden world truth.
- `TM-ENG-006`: Workflow replay shall be identical for same seed+config inputs.
- `TM-ENG-007`: Live Orket integration execution shall preserve parity with scaffold contract behavior for pinned fixtures.

### 5.2 Gameplay
- `TM-GP-001`: NPC response mode per question shall be exactly one of `truth`, `refuse`, `dont_know`.
- `TM-GP-002`: Facts surfaced in play shall map to existing fact IDs in `WorldGraph`.
- `TM-GP-003`: Every run shall include non-primary secrets to create refusal noise.
- `TM-GP-004`: Scene intro text shall be crisp, 3-6 lines.
- `TM-GP-005`: Runs shall select 4 NPCs from a fixed pool.
- `TM-GP-006`: At least 1-2 canonical time anchors shall always have answer paths.
- `TM-GP-007`: `WorldGraph` shall include at least one access anchor and at least one linkage anchor.
- `TM-GP-008`: Culprit identification shall be non-trivial; a single incriminating refusal cannot be a guaranteed proof.
- `TM-GP-009`: Normal mode shall enforce at least 2 overlapping refusal domains; hard mode (optional v1) shall enforce at least 3.
- `TM-GP-010`: Reveal graph shall expose culprit chain, all NPC secrets, guard domains, knowledge slices, and anchors.
- `TM-GP-011`: Crime tone shall bias toward audacious corporate satire and cultural spectacle incidents, not cozy mystery pacing.
- `TM-GP-012`: NPC roster target is a fixed pool of about 15 named archetypes with stable refusal textures and answer/dont_know/refuse style rules.

### 5.3 User Considerations
- `TM-UX-001`: Player shall ask unrestricted free-text questions.
- `TM-UX-002`: Accusation action shall require explicit confirmation before lock.
- `TM-UX-003`: Companion shall only react to player-visible transcript context.
- `TM-UX-004`: Companion nudges shall be occasional and configurable via thresholds and temperament.
- `TM-UX-005`: Project shall run local-only with no required cloud dependency in v1.
- `TM-UX-006`: Companion memory persistence is mandatory and player-centric (preferences, behavior, session metadata), excluding plot truth.
- `TM-UX-007`: Companion may very rarely reference real-world session time only when grounded in persisted metadata.
- `TM-UX-008`: Boot ritual target is triple-layer "hello" with fading echo/reverb into normal dry voice behavior.

## 6. Quality Requirements
- `TM-QR-001` Determinism: same seed+config gives equivalent `WorldGraph`, decisions, and outcome.
- `TM-QR-002` Safety: no fabricated facts from NPC response layer.
- `TM-QR-003` Explainability: reveal output must make verdict auditable.
- `TM-QR-004` Performance: typical local run interaction latency should feel immediate for deterministic path.
- `TM-QR-005` Privacy: companion memory stores player prefs/stats only.

## 7. Data Contracts (minimum)
- `WorldGraph`: scene, selected NPCs, culprit, primary crime, facts, knowledge map, guard map, secrets, access graph, time anchors.
- `Transcript`: timestamp, npc, raw question, canonical tags, decision, response, optional companion line.
- `CompanionMemory`: preferences + lightweight aggregate player behavior, no plot secrets.

## 8. Milestone Mapping
- M0: `TM-ENG-002`, `TM-UX-001`, basic loop and config.
- M1: `TM-ENG-001`, `TM-ENG-003`, `TM-ENG-004`, foundational data contracts.
- M2: `TM-GP-001`..`TM-GP-006` deterministic Q/A path.
- M3: `TM-ENG-005`, `TM-UX-003`, `TM-UX-004` companion memory and nudge engine.
- M4: optional local model surface layer with strict fact boundaries.
- M5: optional pluggable TTS hook and boot ritual voice behavior.

## 9. Acceptance Criteria (v1 demo)
- Solvable run in 10-20 minutes.
- Wrong accusation hard-ends and reveals full graph.
- No NPC fact hallucinations.
- Companion does not leak hidden truth.
- Replay consistency holds for seed+config.
