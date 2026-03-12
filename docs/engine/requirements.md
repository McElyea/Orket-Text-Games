# Engine Requirements

Primary domain: engine
Related domains: gameplay, user-considerations

## Architecture Boundary
- Client is presentation only.
- Game Orchestrator owns run state and transcript assembly.
- Orket owns deterministic workflow orchestration and artifact persistence.

## Requirements
- `TM-ENG-010`: Implement `GenerateWorld(seed, scene_template_id, npc_selection)` as first immutable step.
- `TM-ENG-011`: Persist run artifact bundle (`world_graph`, `transcript`, `outcome`, `reveal_graph`) for replay and debugging.
- `TM-ENG-012`: Enforce turn-state machine: `open -> questioned* -> accused -> revealed -> closed`.
- `TM-ENG-013`: Reject any post-accusation question input.
- `TM-ENG-014`: Companion nudge engine input is transcript-only view model.
- `TM-ENG-015`: Decision node outputs must be structured (`AnswerDecision`) before text rendering.
- `TM-ENG-016`: Provide deterministic mode tests for seed consistency and accusation consistency.

## Determinism Rules
- Freeze `WorldGraph` after generation.
- No mutation of hidden truth during run.
- Response renderer cannot inject unsupported entities/facts.

## Persistence Rules
- Persist `CompanionMemory` separately from per-run truth data.
- Never merge hidden run truth into companion memory.

## Validation Targets
- Unit tests for world generation determinism.
- Golden tests for turn pipeline transitions.
- Replay test validates outcome equivalence from stored artifacts.
