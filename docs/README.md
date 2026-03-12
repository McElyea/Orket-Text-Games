# TextMystery Documentation

This project uses a split docs model:
- `docs/engine`: Orket runtime, deterministic workflow, integration contracts, persistence boundaries.
- `docs/gameplay`: game rules, content system, world generation, accusation/reveal mechanics.
- `docs/user-considerations`: player-facing behavior, UX constraints, companion behavior, privacy/local-only expectations.
- `docs/strategy`: roadmap, milestone slicing, delivery sequencing.

Primary entry points:
- `docs/SRS.md`
- `docs/strategy/implementation-strategy.md`
- `docs/strategy/thread-decisions-addendum.md`
- `docs/engine/classification-micro-spec.md`
- `docs/engine/live-endpoint-contract.md`

Conventions:
- Requirements use stable IDs (`TM-ENG-*`, `TM-GP-*`, `TM-UX-*`).
- Each requirement has an acceptance target and milestone mapping (`M0`..`M5`).
- Cross-cutting docs are allowed when useful, but each doc should identify its primary domain.
