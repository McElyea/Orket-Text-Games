from __future__ import annotations

import hashlib
import random
from typing import Any

from .persist import canonical_world_digest
from .types import Fact, WorldGraph


def _rng_seed(seed: int, scene_id: str, npc_ids: list[str], difficulty: str) -> int:
    material = f"{seed}|{scene_id}|{','.join(npc_ids)}|{difficulty}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest()[:16], 16)


def generate_world(
    seed: int,
    scene_id: str,
    npc_ids: list[str],
    difficulty: str,
    config: dict[str, Any],
) -> WorldGraph:
    """Generate a deterministic frozen world graph for a run.

    TS mapping: TS-DET-001, TS-WORLD-001.
    """
    del config  # reserved for future knobs
    if not npc_ids:
        raise ValueError("npc_ids must be non-empty")

    mode = str(difficulty or "normal").strip().lower()
    if mode not in {"normal", "hard"}:
        raise ValueError("difficulty must be 'normal' or 'hard'")
    if mode == "normal" and len(npc_ids) < 4:
        raise ValueError("normal mode requires at least 4 npc_ids")
    if mode == "hard" and len(npc_ids) < 5:
        raise ValueError("hard mode requires at least 5 npc_ids")

    selected = tuple(npc_ids)
    rng = random.Random(_rng_seed(seed, scene_id, list(selected), mode))
    culprit = selected[rng.randrange(len(selected))]
    witness_candidates = [npc for npc in selected if npc != culprit]
    witness_npc = witness_candidates[rng.randrange(len(witness_candidates))]
    primary_crime_id = "CRIME_CORP_LEAK_001" if rng.random() < 0.5 else "CRIME_SPECTACLE_HIJACK_001"

    facts = {
        "FACT_TIME_ANCHOR_1": Fact(
            "FACT_TIME_ANCHOR_1",
            "time",
            {"kind": "time_anchor", "time": "11:03 PM", "time_code": "11:03"},
        ),
        # Keep this anchor id stable while upgrading payload semantics.
        "FACT_ACCESS_ANCHOR_1": Fact(
            "FACT_ACCESS_ANCHOR_1",
            "access_method",
            {"kind": "access_method", "where": "SERVICE_DOOR", "method": "KEYCARD"},
        ),
        "FACT_PRESENCE_1": Fact(
            "FACT_PRESENCE_1",
            "presence",
            {"kind": "presence", "who": culprit, "where": "SERVICE_DOOR", "when": "11:03 PM"},
        ),
        "FACT_WITNESS_1": Fact(
            "FACT_WITNESS_1",
            "witness",
            {"kind": "witness", "witness": witness_npc, "who": culprit, "where": "SERVICE_DOOR", "when": "11:03 PM"},
        ),
        "FACT_OBJECT_1": Fact(
            "FACT_OBJECT_1",
            "object",
            {"kind": "object", "object": "AUDIT_DRIVE"},
        ),
        "FACT_OBJECT_MOVED_1": Fact(
            "FACT_OBJECT_MOVED_1",
            "action",
            {"kind": "action", "who": culprit, "action": "MOVED", "object": "AUDIT_DRIVE", "when": "11:03 PM", "where": "ARCHIVE"},
        ),
        "FACT_BOARDROOM_FEED_1": Fact(
            "FACT_BOARDROOM_FEED_1",
            "object",
            {"kind": "object", "object": "BOARDROOM_FEED", "state": "HIJACKED"},
        ),
    }

    secret_templates = (
        ("SECRET_FINANCE", "secret_finance", {"kind": "secret", "domain": "FINANCE", "surface": "SURF_MOTIVE", "hint": "OFFBOOK_EXPENSE_SHEET"}),
        ("SECRET_RELATIONSHIP", "secret_relationship", {"kind": "secret", "domain": "RELATIONSHIP", "surface": "SURF_RELATIONSHIP", "hint": "UNDECLARED_CONTACT"}),
        ("SECRET_ACCESS", "secret_access_violation", {"kind": "secret", "domain": "ACCESS", "surface": "SURF_ACCESS", "hint": "BADGE_POLICY_BREACH"}),
    )

    npc_knowledge: dict[str, set[str]] = {}
    npc_guards: dict[str, set[str]] = {}
    npc_secrets: dict[str, str] = {}
    for index, npc in enumerate(selected):
        secret_name, secret_type, secret_payload = secret_templates[index % len(secret_templates)]
        secret_fact_id = f"FACT_{secret_name}_{index + 1}"
        payload = dict(secret_payload)
        payload["npc"] = npc
        facts[secret_fact_id] = Fact(secret_fact_id, secret_type, payload)

        knows = {secret_fact_id}
        if index % 2 == 0:
            knows.add("FACT_TIME_ANCHOR_1")
        if index % 2 == 1:
            knows.add("FACT_ACCESS_ANCHOR_1")
        if npc == culprit:
            knows.update({"FACT_PRESENCE_1", "FACT_OBJECT_1", "FACT_OBJECT_MOVED_1"})
        if npc == witness_npc:
            knows.add("FACT_WITNESS_1")
        npc_knowledge[npc] = knows

        guards = {secret_fact_id}
        if npc == culprit:
            guards.add("FACT_OBJECT_MOVED_1")
        npc_guards[npc] = guards
        npc_secrets[npc] = f"SECRET_{secret_name}_{npc}"

    # Guarantee answerable unguarded anchors.
    for required in ("FACT_TIME_ANCHOR_1", "FACT_ACCESS_ANCHOR_1", "FACT_PRESENCE_1", "FACT_WITNESS_1"):
        if not any(required in npc_knowledge[n] and required not in npc_guards[n] for n in selected):
            npc_knowledge[selected[0]].add(required)
            npc_guards[selected[0]].discard(required)
    # Cooperative anchor rule: one non-culprit NPC must provide core anchors.
    cooperative = next((npc for npc in selected if npc != culprit), selected[0])
    for required in ("FACT_TIME_ANCHOR_1", "FACT_ACCESS_ANCHOR_1", "FACT_WITNESS_1"):
        npc_knowledge[cooperative].add(required)
        npc_guards[cooperative].discard(required)

    base_world = WorldGraph(
        scene_template_id=scene_id,
        selected_npc_ids=selected,
        culprit_npc_id=culprit,
        primary_crime_id=primary_crime_id,
        facts=facts,
        npc_knowledge=npc_knowledge,
        npc_guards=npc_guards,
        npc_secrets=npc_secrets,
        access_graph={
            "SERVICE_DOOR": [culprit, selected[0]],
            "BOARDROOM": [selected[-1]],
            "ARCHIVE": [culprit],
        },
        lead_unlocks={
            "LEAD_WITNESS_1": ("disc:fact:FACT_WITNESS_1", "disc:place:SERVICE_DOOR", f"disc:npc:{culprit}"),
            "LEAD_PRESENCE_1": ("disc:fact:FACT_PRESENCE_1", "disc:place:SERVICE_DOOR", f"disc:npc:{culprit}"),
            "LEAD_OBJECT_1": ("disc:fact:FACT_OBJECT_1", "disc:object:AUDIT_DRIVE"),
            "LEAD_ACTION_1": ("disc:fact:FACT_OBJECT_MOVED_1", "disc:place:ARCHIVE", "disc:object:AUDIT_DRIVE"),
        },
        time_anchors=("FACT_TIME_ANCHOR_1",),
        access_anchors=("FACT_ACCESS_ANCHOR_1",),
        linkage_anchors=("FACT_PRESENCE_1", "FACT_WITNESS_1"),
        digest="",
    )
    _assert_playability_invariants(base_world)
    digest = canonical_world_digest(base_world)
    return WorldGraph(
        scene_template_id=base_world.scene_template_id,
        selected_npc_ids=base_world.selected_npc_ids,
        culprit_npc_id=base_world.culprit_npc_id,
        primary_crime_id=base_world.primary_crime_id,
        facts=base_world.facts,
        npc_knowledge=base_world.npc_knowledge,
        npc_guards=base_world.npc_guards,
        npc_secrets=base_world.npc_secrets,
        access_graph=base_world.access_graph,
        lead_unlocks=base_world.lead_unlocks,
        time_anchors=base_world.time_anchors,
        access_anchors=base_world.access_anchors,
        linkage_anchors=base_world.linkage_anchors,
        digest=digest,
    )


def _assert_playability_invariants(world: WorldGraph) -> None:
    # INV-PLAY-1: triangulation through witness + presence over the same place.
    witness = world.facts.get("FACT_WITNESS_1")
    presence = world.facts.get("FACT_PRESENCE_1")
    witness_payload = witness.value if isinstance(witness and witness.value, dict) else {}
    presence_payload = presence.value if isinstance(presence and presence.value, dict) else {}
    if not isinstance(witness_payload, dict) or not isinstance(presence_payload, dict):
        raise ValueError("playability invariant failed: missing typed witness/presence payloads")
    if witness_payload.get("kind") != "witness" or presence_payload.get("kind") != "presence":
        raise ValueError("playability invariant failed: invalid witness/presence kind")
    if witness_payload.get("who") != presence_payload.get("who"):
        raise ValueError("playability invariant failed: witness/presence mismatch")
    if witness_payload.get("where") != presence_payload.get("where"):
        raise ValueError("playability invariant failed: witness/presence place mismatch")

    # INV-PLAY-2: typed answerability for key anchors.
    if "time" not in (world.facts["FACT_TIME_ANCHOR_1"].value or {}) or world.facts["FACT_TIME_ANCHOR_1"].value.get("kind") != "time_anchor":
        raise ValueError("playability invariant failed: time anchor missing time field")
    if "method" not in (world.facts["FACT_ACCESS_ANCHOR_1"].value or {}) or world.facts["FACT_ACCESS_ANCHOR_1"].value.get("kind") != "access_method":
        raise ValueError("playability invariant failed: access anchor missing method field")
    if "who" not in (world.facts["FACT_WITNESS_1"].value or {}) or world.facts["FACT_WITNESS_1"].value.get("kind") != "witness":
        raise ValueError("playability invariant failed: witness anchor missing who field")

    # INV-PLAY-3: escalation surfaces exist in generated case.
    if not world.time_anchors or not world.access_anchors or not world.linkage_anchors:
        raise ValueError("playability invariant failed: missing required anchor families")
    if not {"SERVICE_DOOR", "BOARDROOM", "ARCHIVE"}.issubset(set(world.access_graph.keys())):
        raise ValueError("playability invariant failed: missing canonical place ids")
