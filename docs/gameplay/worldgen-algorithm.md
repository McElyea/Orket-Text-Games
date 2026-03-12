# Worldgen Algorithm (v1)

Primary domain: gameplay
Related domains: engine

Goal: deterministic seeded generator that always produces a solvable case with controlled refusal noise.

## Inputs
- `seed`
- `scene_template_id`
- `npc_ids` (4 default; 5-6 for hard mode)
- `difficulty` (`normal` or `hard`)

## Output
Frozen `WorldGraph` including:
- `culprit_npc_id`
- `primary_crime_id`
- `facts: {fact_id -> (type, value)}`
- `npc_knowledge[npc_id] -> set(fact_id)`
- `npc_guards[npc_id] -> set(fact_id)`
- `npc_secrets[npc_id] -> secret_id`
- `time_anchors`
- `access_anchors`
- `linkage_anchors`

## Deterministic Generation Steps

### 1. Initialize RNG
- Initialize RNG from `seed`.
- All stochastic choices must consume this RNG only.

### 2. Select Primary Crime
- Choose crime from scene template palette using weighted distribution.
- Theme bias favors Corporate Satire and Cultural Spectacle.

### 3. Select Culprit
- Choose culprit from selected NPCs (uniform by default).

### 4. Instantiate Required Fact Slots
Populate minimum fact chain:
- time anchor fact
- access anchor fact
- linkage anchor fact
- key object fact
- key action fact

### 5. Assign Knowledge
- Ensure at least one non-culprit knows at least one anchor fact.
- Ensure culprit knows sufficient facts to be cornered.
- Avoid making culprit identifiable from refusal-only pattern.
- Ensure at least one innocent has a refusal tied to non-primary secret that can sound incriminating out of context.

### 6. Assign Secrets and Guards
- Assign one non-primary secret per NPC.
- Build guard sets over fact IDs.
- Enforce refusal overlap:
  - normal: at least 2 NPC guard domains overlap on meaningful surface area
  - hard: at least 3 overlap
- Preserve answerability by keeping required anchors unguarded somewhere.

### 7. Validate Solvability
Run structural validator (not an AI solver):
- anchors exist and are answerable
- at least one fact-based elimination path exists to culprit
- refusal overlap present but non-trivial
- primary culprit cannot be inferred from a single binary accusation-style refusal pattern

If invalid:
- reroll via deterministic next RNG state
- bounded attempts
- fail loudly if max attempts exceeded

## Solvability Invariants
- `INV-ANCHOR-1`: At least one answerable time anchor.
- `INV-ANCHOR-2`: At least one answerable access anchor.
- `INV-ANCHOR-3`: At least one answerable linkage anchor.
- `INV-NOISE-1`: Refusal overlap present (`normal >= 2`, `hard >= 3`).
- `INV-NONTRIVIAL-1`: Culprit not inferable from single incriminating refusal pattern.
- `INV-GRAPH-REVEAL`: Every refusal can be explained by guard cause in reveal graph.

## Suggested Validator Interface
`validate_worldgraph(world_graph, difficulty) -> ValidationResult`
- `ok: bool`
- `failed_invariants: list[str]`
- `diagnostics: dict`

## Failure Policy
- If generation fails after bounded attempts:
  - emit deterministic error payload with failed invariant list
  - do not start run

## Versioning
- Include algorithm version in artifact metadata.
- Replay checks should pin generator version for hash parity.
