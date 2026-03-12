# Local-Only, Privacy, and Safety Notes

Primary domain: user-considerations
Related domains: engine

## Local-Only Principle
- v1 must operate without cloud dependencies.
- Any optional local model/TTS provider is process-local and user-configured.

## Data Handling
- Store only local artifacts under project-controlled directories.
- Separate per-run artifacts from persistent companion memory.
- No telemetry export by default.

## Safety Constraints
- NPCs cannot invent facts.
- Companion cannot access hidden world graph.
- Reveal graph must be available after every accusation to preserve trust and explainability.

## Optional Local Model Guardrails (M4)
- Model receives only structured decision payload from deterministic resolver.
- Apply lightweight named-entity allowlist post-check.
- On violation, fall back to deterministic template renderer.
