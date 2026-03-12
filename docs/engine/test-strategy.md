# Test Strategy

Primary domain: engine
Related domains: gameplay, user-considerations

Scope: determinism, truth-safety, refusal correctness, companion non-leak, replayability, and no-new-facts constraints.

## Test Suites
- `TS-DET`: Determinism and replay
- `TS-CLASS`: Canonical query classification and fallback determinism
- `TS-CONTENT`: Content schema and referential integrity
- `TS-TRUTH`: Truth / refuse / dont_know correctness
- `TS-LEAK`: No new facts / no hidden-state leakage
- `TS-WORLD`: Worldgen solvability invariants
- `TS-COMP`: Companion constraints (transcript-only visibility)
- `TS-UX`: Timing and run-length sanity

## Core Harness
- Test framework: `pytest`
- Two layers:
  - `tests/`: fast deterministic unit/scaffold tests
  - `tests_integration/`: live Orket integration tests exercising runtime boundaries
- Live test env controls:
  - `TEXTMYSTERY_RUN_LIVE=1`
  - `TEXTMYSTERY_ORKET_BASE_URL=<local-orket-base-url>`
- Example:
  - `python -m pytest -m ts_live`
- Snapshot/golden approach:
  - WorldGraph golden JSON
  - Transcript golden JSON
  - RevealGraph golden JSON
- Suggested utilities:
  - golden compare helper (`tests/golden/`)
  - CLI debug dump command:
    - `--seed`
    - `--scene`
    - `--npcs`
    - `--dump-world`
    - `--dump-reveal`

## Must-Have Cases

### TS-DET-001 Seed Replay Parity
Given identical `{seed, scene_id, npc_ids, settings}`:
- `WorldGraph` hash is identical.
- For fixed transcript inputs, decision outputs are identical.
- RevealGraph is identical.
- Any random source must be seed-derived.

Pass criteria:
- 100% parity across repeated runs in same runtime version.

### TS-LIVE-001 Runtime Parity (Orket Integration)
For pinned seed/config fixtures, execute the same interrogation transcript through Orket runtime flow and assert parity with scaffold expectations:
- same decision sequence (`ANSWER/REFUSE/DONT_KNOW`)
- same reveal outcome and graph digest
- same resume validation result

### TS-LIVE-002 No-Leak Parity (Orket Integration)
Run live integration path and assert:
- NPC responses do not introduce unauthorized entities/facts
- companion output stays transcript-only and non-leaky

### TS-DET-RESUME-001 Save/Load Resume Parity
Given persisted run header (`seed`, `scene_id`, `npc_ids`, `difficulty`, `content_version`, `generator_version`, `world_digest`):
- resume validation accepts matching current versions
- resumed run preserves deterministic parity

### TS-DET-RESUME-002 Resume Invalidation On Drift
If `content_version` or `generator_version` mismatches:
- resume is invalidated deterministically
- runtime must reject gameplay resume and allow reveal-only path when available

### TS-CLASS-001 Ambiguity Resolution
Ambiguous questions resolve by deterministic priority and tie-break rules, or produce `UNCLASSIFIED_AMBIGUOUS` with `SURF_UNKNOWN`.

### TS-CLASS-CONF-001 Confidence Stability
For same text input, confidence is stable and in `[0.0, 1.0]`.
Confidence must derive from classifier scoring only.

### TS-CLASS-TIE-001 Deterministic Tie Break
Equal-score ties resolve via fixed ordering rules (intent id, surface id, object id) with no randomness.

### TS-WORLD-001 Always-Solvable Anchors
Generated world must satisfy:
- At least one answerable, unguarded time anchor fact.
- At least one answerable, unguarded access anchor fact.
- At least one answerable, unguarded linkage anchor fact.
- At least one fact-based linkage path from discoverable facts to culprit identification.

If constraints fail:
- generation fails and rerolls (bounded),
- hard failure if bounded rerolls exhausted.

### TS-TRUTH-001 Decision Correctness
For a resolved `fact_id` query and target NPC:
- If `fact_id in npc_knowledge` and `fact_id not in npc_guards` -> `ANSWER`
- If `fact_id in npc_guards` -> `REFUSE`
- Else -> `DONT_KNOW`

Pass criteria:
- rule holds across matrix of NPCs, facts, and intents.

### TS-LEAK-001 No New Named Entities in NPC Response
Per run allowlist includes:
- active NPC names
- scene objects
- canonical places

Assert NPC response text contains no out-of-allowlist entities.
Assert response includes no fact values beyond authorized `fact_id` payload.

Note:
- Start with deterministic token/entity matcher; harden later with stricter parser.

### TS-LEAK-SURF-001 Surface Probe Does Not Leak Facts
`WHAT_DO_YOU_KNOW_ABOUT` style surface probes must not return new `fact_id`, unseen entities, or undiscovered specific details.

### TS-COMP-001 Companion Cannot Reference Hidden Truth
Companion generator input excludes hidden fields:
- culprit identity
- guard maps/reasons
- secret identifiers

Fuzz transcript inputs and assert companion lines never include:
- culprit name with accusatory framing
- guard reason disclosure
- secret ID/value leakage

### TS-COMP-NUDGE-001 Nudge Threshold Compliance
Companion nudges should trigger only after configured stall thresholds and must remain non-leaky.

### TS-CONTENT-001 Content Integrity
Validate ID regex (`^[A-Z0-9_]+$`), uniqueness, and referential integrity across NPCs, scenes, crimes, secrets, guards, and refusal styles.

### TS-UX-001 Turn Budget Sanity
For `N` generated worlds and a baseline interrogator bot:
- median turn count <= `X` (default target: 12-18)
- p95 turn count <= `Y` (default target: 25)

Purpose:
- catch degenerate worlds that are too opaque or too noisy.

## Additional Recommended Cases
- `TS-DET-002` Different seeds produce non-identical world hashes.
- `TS-WORLD-002` Each refusal in transcript has explainable guard cause in RevealGraph.
- `TS-TRUTH-002` No truthful response for unknown facts.
- `TS-LEAK-002` Optional LLM surface mode blocks unauthorized entities and falls back safely.
- `TS-COMP-002` Companion nudge frequency respects threshold and temperament settings.

## Milestone Mapping
- M0: harness scaffolding and golden infrastructure
- M1: `TS-DET-001`, `TS-WORLD-001`, accusation/reveal parity checks
- M2: `TS-TRUTH-*`, `TS-LEAK-001`
- M3: `TS-COMP-*`
- M4: optional LLM guardrail tests (`TS-LEAK-002`)
- M5: optional TTS behavior smoke tests
- Integration track: add `TS-LIVE-*` starting M2 and require green before v1 demo freeze.
