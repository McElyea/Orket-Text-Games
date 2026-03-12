# Interaction Copy Guidelines (v1)

Primary domain: user-considerations
Related domains: gameplay

Goal: keep NPC output legible and flavorful while preserving strict truth boundaries and companion non-leak behavior.

## Hard Output Constraints
- NPC response must not introduce facts beyond resolved `fact_id` payload.
- If decision is `REFUSE`, response must not explain why.
- If decision is `DONT_KNOW`, response must not speculate.
- Companion line must not reference hidden truth fields.

## NPC Response Modes

### ANSWER
- 1-2 sentences max.
- Exact factual wording.
- No extra names/entities outside allowed set.

### REFUSE
- One short line or equivalent terse form.
- No guard reason hints.
- No implied confession language.

### DONT_KNOW
- Short, neutral ignorance statement.
- No conjecture.

## Archetype Template Pattern
Each NPC archetype defines:
- ANSWER templates
- REFUSE templates
- DONT_KNOW templates

Example style targets:
- Gabe (Security)
  - ANSWER: "I was at the service door at 11:03."
  - REFUSE: "Next."
  - DONT_KNOW: "Not my area."
- Nadia (HR/Empath)
  - ANSWER: "Yes, keycards were reissued this morning."
  - REFUSE: "I can't share that."
  - DONT_KNOW: "I wasn't told."

## Companion Nudge Guidelines
- Never accusatory.
- Never names culprit.
- Pattern-based nudges only:
  - repetition signals
  - refusal clusters
  - surface-area hints (for example, recurring location/object)
- Frequency controlled by thresholds and temperament.
- Default temperament should be sparse and "nice".
- Companion tone should stay playful/mysterious but non-confrontational.

## Boot Ritual Copy
- Triple-layer "hello" style intro.
- Initial spatial target: right-side, slightly behind listener impression (if audio stack supports it).
- Settle into sparse companion behavior after intro.
- Intro should frame tone without revealing mechanics-heavy details.

## Copy QA Checklist
- Does line contain unauthorized entity/value?
- Does refusal imply hidden reason?
- Does dont_know speculate?
- Does companion line imply culprit or secret?
- Is response length concise and archetype-consistent?

## Iteration Note
Finalize broad copy pass after M1/M2 mechanics settle to reduce rewrite churn.
Avoid over-explaining system internals in player-facing text; keep the experience diegetic.
