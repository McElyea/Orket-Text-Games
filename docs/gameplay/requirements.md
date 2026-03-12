# Gameplay Requirements

Primary domain: gameplay
Related domains: engine, user-considerations

## Core Loop
1. Start run with seed.
2. Select scene and 4 NPCs.
3. Player chooses NPC and asks free-text question.
4. NPC returns truth/refuse/dont_know response.
5. Companion may emit nudge.
6. Repeat until player accuses.
7. Lock run and reveal full graph.

## Requirements
- `TM-GP-010`: Exactly one primary crime per run.
- `TM-GP-011`: Every NPC has at least one secondary secret (or equivalent guard behavior) to create refusal noise.
- `TM-GP-012`: NPC never lies.
- `TM-GP-013`: `dont_know` must be used when fact not known by the NPC knowledge map.
- `TM-GP-014`: `refuse` must map to guard-protected facts.
- `TM-GP-015`: Truth answers must map to exact fact IDs.
- `TM-GP-016`: Intro copy per scene must be 3-6 lines.
- `TM-GP-017`: Content theme distribution biased toward Corporate Satire + Cultural Spectacle.
- `TM-GP-018`: `WorldGraph` must include time, access, and linkage anchors.
- `TM-GP-019`: At least one innocent NPC must have an incriminating-feeling refusal domain so primary guilt is not implied by one refusal.
- `TM-GP-020`: Normal mode uses 4 NPCs and requires at least 2 overlapping refusal surface areas.
- `TM-GP-021`: Hard mode (optional in v1) uses 5-6 NPCs and requires at least 3 overlapping refusal surface areas.
- `TM-GP-022`: Free-text input is always accepted, but all interrogation decisions use canonical deterministic query categories.
- `TM-GP-023`: Typical runs should be tuned to approximately 8-15 meaningful exchanges to support 10-20 minute sessions.

## WorldGraph Minimum Content
- culprit
- primary crime
- required fact path
- access graph
- time anchors
- linkage anchors
- npc knowledge map
- npc guard map
- npc secrets

## Accusation Rules
- Single-shot accusation.
- Confirmation gate before submit.
- No further questions after submission.
- Always show reveal graph.

## Success Metrics (v1)
- Median completion in 10-20 minutes.
- High explainability of outcome from reveal graph.
- Refusal noise is present in all runs without making runs unsolvable.
