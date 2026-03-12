# Content System Spec (v1)

Primary domain: gameplay

## NPC Pool
- Start target: 15 named NPCs.
- Milestone M1/M2 bootstrap: at least 8 NPCs.
- Each NPC defines:
  - archetype
  - refusal texture
  - linguistic style tags
- Strong v1 anchors should include: Nick Vale, Nadia Bloom, Victor Slate, Gabe Rourke.

## Scene Templates
- Start with 1-2 scene templates.
- Expand to 5+ later.
- Each scene template includes:
  - intro lines (3-6)
  - eligible crimes
  - required entities/objects
  - timeline anchors

## Facts and Secrets
- Facts are exact, atomic, and ID-based.
- No speculative facts.
- Primary crime facts are solvable via at least one path.
- Non-primary secrets should introduce plausible refusal noise.

## Theme Bias
- Weighted generator with bias:
  - Corporate Satire (higher)
  - Cultural Spectacle (higher)
  - Others (lower)
- Crime setup should feel brazen/public/famous-style, not cozy domestic mystery.

## Authoring Constraints
- Avoid ambiguous wording in fact text.
- Keep refusal lines expressive but non-informative about hidden facts.
- Keep response style consistent per NPC archetype.
- Keep scene intros concise (3-6 lines): timestamp, what happened, what's weird, suspects.
