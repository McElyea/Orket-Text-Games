from __future__ import annotations

from .types import RevealGraph, WorldGraph


def compute_reveal(world: WorldGraph, accused_npc_id: str) -> RevealGraph:
    """Compute accusation outcome and full reveal graph.

    v1 shape keeps verdict details derivable from payload:
    - culprit/primary chain always shown
    - refusal causes expanded from guard domains
    """
    del accused_npc_id  # verdict details can be derived by comparing with culprit outside this payload
    refusal_causes: dict[str, str] = {}
    for npc_id, guarded_fact_ids in world.npc_guards.items():
        if not guarded_fact_ids:
            continue
        for fact_id in sorted(guarded_fact_ids):
            refusal_causes[f"{npc_id}:{fact_id}"] = world.npc_secrets.get(npc_id, "SECRET_UNKNOWN")
    return RevealGraph(
        culprit_npc_id=world.culprit_npc_id,
        primary_crime_id=world.primary_crime_id,
        refusal_causes=refusal_causes,
        facts=world.facts,
    )
