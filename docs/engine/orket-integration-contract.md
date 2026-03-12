# Orket Integration Contract

Primary domain: engine

## Workflow Nodes (v1)
1. `GenerateWorld`
2. `ClassifyQuestion`
3. `ResolveAnswer`
4. `RenderNPCResponse`
5. `MaybeNudge`
6. `ResolveOutcome`
7. `EmitRevealGraph`

## Node Contracts

### GenerateWorld
Input:
- `seed`
- `scene_template_id`
- `selected_npc_ids`
Output:
- `WorldGraph`

### ClassifyQuestion
Input:
- `raw_text`
- `transcript_visible_context`
Output:
- `CanonicalQuery { intent, entities, specificity? }`

### ResolveAnswer
Input:
- `world_graph`
- `npc_id`
- `canonical_query`
Output:
- `AnswerDecision { mode, fact_id?, refusal_reason? }`
Where `mode in {truth, refuse, dont_know}`

### RenderNPCResponse
Input:
- `npc_persona`
- `answer_decision`
Output:
- `response_text`
Constraint:
- no new facts outside selected fact/refusal mode

### MaybeNudge
Input:
- `transcript_visible_context`
- `companion_settings`
Output:
- optional `companion_line`
Constraint:
- cannot consume hidden graph

### ResolveOutcome
Input:
- `world_graph`
- `accused_npc_id`
Output:
- `Outcome { win|lose }`

### EmitRevealGraph
Input:
- `world_graph`
- `outcome`
Output:
- `RevealGraph` (always)

## Error Policy
- Invalid NPC or invalid phase transitions return deterministic errors.
- Post-accusation question attempts return locked-state error.

## Optional LLM Surface Mode (M4)
- LLM usage is render-only, not decision authority.
- Response post-check blocks text with unauthorized entities.
