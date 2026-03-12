# User Considerations Requirements

Primary domain: user-considerations
Related domains: gameplay

## Player Experience Goals
- Fast onboarding with atmospheric intro.
- High agency through free text questioning.
- Clear one-shot accusation stakes.
- Companion presence that feels helpful but not overbearing.

## Requirements
- `TM-UX-010`: Boot ritual includes companion hello presence layer before first turn.
- `TM-UX-011`: Player can target any active NPC each turn.
- `TM-UX-012`: Player can ask unrestricted free text each turn.
- `TM-UX-013`: Settings expose hint thresholds and companion temperament.
- `TM-UX-014`: Companion nudges are optional, sparse, and context-derived from visible transcript.
- `TM-UX-015`: Accusation confirmation explains finality.
- `TM-UX-016`: Reveal graph presentation is readable in text-first format.
- `TM-UX-017`: Companion memory persistence across runs is required in v1.
- `TM-UX-018`: Companion must remain non-confrontational and non-competitive by default.
- `TM-UX-019`: Rare real-world-time callback lines are allowed only from persisted session metadata and should stay uncommon.

## Companion Memory
- Persist:
  - temperament
  - voice selection
  - hint settings
  - lightweight aggregate behavior
  - session metadata needed for rare grounded time callbacks
- Never persist:
  - culprit memory
  - world secrets
  - hidden run graph facts

## UX Failure Cases to Prevent
- accidental accusation submission
- hidden-knowledge companion hints
- unclear refusal vs dont_know distinction
- muddy reveal output after loss
- companion time-reference behavior feeling creepy or too frequent
