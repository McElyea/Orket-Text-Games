"""TS-CLASS-001: Ambiguous input resolves deterministically. Milestone: M1."""

import pytest

from textmystery.engine.classify import classify_question
from textmystery.engine.types import IntentId

pytestmark = [pytest.mark.ts_class, pytest.mark.milestone_m1]


def test_ts_class_001_ambiguous_deterministic_resolution(sample_npc_ids):
    q = classify_question("When and where were you during the outage?", sample_npc_ids, {})
    assert q.intent_id in {IntentId.WHEN_WAS, IntentId.WHERE_WAS, IntentId.UNCLASSIFIED_AMBIGUOUS}
    q2 = classify_question("When and where were you during the outage?", sample_npc_ids, {})
    assert q.intent_id == q2.intent_id
    assert q.surface_id == q2.surface_id


def test_ts_class_001_phrase_first_witness_beats_location_overlap(sample_npc_ids):
    q = classify_question("Who did you see near the service door?", sample_npc_ids, {})
    assert q.intent_id == IntentId.DID_YOU_SEE


def test_ts_class_001_access_to_object_routes_to_did_you_do(sample_npc_ids):
    q = classify_question("Did you have access to the audit drive?", sample_npc_ids, {})
    assert q.object_id == "AUDIT_DRIVE"
    assert q.intent_id == IntentId.DID_YOU_DO


def test_ts_class_001_witness_shorthand_near_place_prefers_witness(sample_npc_ids):
    q = classify_question("see near service door?", sample_npc_ids, {})
    assert q.intent_id == IntentId.DID_YOU_SEE
    assert q.place_ref == "SERVICE_DOOR"


def test_ts_class_001_who_can_confirm_maps_to_relationship(sample_npc_ids):
    q = classify_question("who can confirm that?", sample_npc_ids, {})
    assert q.intent_id == IntentId.WHO_WAS_WITH
