# Thread Decisions Addendum

Primary domain: strategy
Related domains: engine, gameplay, user-considerations

## Intent
- This is a local toy/demo project for friends.
- Priority is momentum and shipping a playable loop, not perfect content completeness.
- The experience should showcase controlled local AI without surfacing internal governance concepts.

## Locked v1 Gameplay Decisions
- Detective interrogation loop with one hard accusation.
- NPCs can only: truthful answer, refuse, or say they do not know.
- Everyone has one non-primary secret, so refusals are noisy by design.
- Exactly one NPC is guilty of the primary crime in a run.
- Free-text input remains open, while internal resolution uses deterministic canonical query categories.
- Accusation is one-shot, then full reveal graph ends the run (win or lose).

## Run Length and Pace
- Target run duration: 10-20 minutes.
- Target interaction budget: about 8-15 meaningful exchanges.
- Do not force exhaustive questioning once player is ready to accuse.

## Difficulty
- Normal: 4 NPCs, refusal overlap on at least 2 shared surface areas.
- Hard (optional v1/future): 5-6 NPCs, refusal overlap on at least 3 shared surface areas.

## WorldGraph and Determinism
- WorldGraph is precomputed before first interrogation turn and frozen.
- Must include:
  - one primary crime chain,
  - one culprit among selected NPCs,
  - one non-primary secret per NPC,
  - guard domains derived from secrets,
  - knowledge slices for exact fact answerability.
- Facts are exact-only in v1: no speculation, no partial fact invention.
- Must include solvability anchors:
  - at least one time anchor,
  - at least one access anchor,
  - at least one linkage anchor.
- Non-triviality constraint:
  - culprit cannot be identified from a single accusation-style refusal;
  - at least one innocent must refuse around an unrelated but suspicious surface.

## Tone and Content Direction
- Avoid cozy pacing and long scenic exposition.
- Favor audacious, famous-feeling crimes with crisp intros (3-6 lines).
- Bias content toward:
  - corporate satire incidents,
  - cultural spectacle disruptions.
- Victim is optional; sabotage/theft/fraud/disruption are valid outcomes.

## NPC Pool Direction
- Target fixed pool: about 15 named exaggerated archetypes.
- Each NPC has fixed demeanor, refusal texture, and style for answer/dont_know/refuse.
- Core anchor names include Nick Vale, Nadia Bloom, Victor Slate, Gabe Rourke.

## Companion Decisions
- Companion is a gentle presence, not an opponent.
- Companion can only see player-visible transcript.
- Persistent companion memory across runs is mandatory and player-centric.
- No fake aging/learning arc in v1.
- Nudge frequency and temperament are configurable.
- Boot ritual target: triple-overlapping "hello" with fading echo/reverb into dry voice.
- Rare real-world-time callbacks are allowed only when grounded in persisted session metadata.

## Out of Scope for v1
- Glitch carryover NPC memory mechanics.
- Direct in-run companion conversation mode.

## Reveal Graph Requirements
On accusation, always reveal:
- culprit + primary crime chain,
- each NPC secret,
- guard domains and refusal causes,
- knowledge slices,
- timeline/access/linkage anchors.

## Implementation Guidance
- Keep free-text UX, but canonicalize internally (`time`, `location`, `access`, `object`, `person`, `alibi`, `motive`, and similar).
- Decision authority remains deterministic graph logic.
- Optional generation models may only phrase already-decided outputs and must not introduce new facts.
