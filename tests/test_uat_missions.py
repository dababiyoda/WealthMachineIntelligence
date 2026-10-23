"""UAT mission control record tests.

The group-chat design's own setup test, run against the record that
enforces it: one synthetic mission through Revenue -> Delivery ->
independent acceptance -> economic reconciliation -> Compounding, then the
named safe failures — missing artifact, duplicate claim, unsupported
commercial assertion, expired grant, reviewer rejection, absent
permission and an uncertain external result. No real effect is needed.
"""
from datetime import datetime, timedelta, timezone

import pytest

from src.services.uat_missions import (GROUPS, ROSTER, ControlRecord, Grant, MissionRefusal,
                                       validate_roster)

NOW = datetime(2026, 10, 23, 15, 0, tzinfo=timezone.utc)


def _contract(**kw):
    base = dict(mission_id="M-SYN-001", venture_id="V-SYN", owner="Concord",
                reviewer="Veritas", bounded_outcome="one refundable pilot proposal",
                active_bottleneck="first paid commitment",
                acceptance_criteria="buyer-readable scope, price, acceptance test",
                deadline="2026-10-26T17:00-04:00", origin_group="Revenue & Partnerships",
                synthetic=True)
    base.update(kw)
    return base


def _running(rec, **kw):
    m = rec.open(**_contract(**kw))
    for state in ("SCOPED", "AUTHORIZED", "READY", "RUNNING"):
        rec.transition(m.mission_id, state, by=m.owner)
    return m


def _packet(m, to_bot, **kw):
    base = dict(mission_id=m.mission_id, artifact_ref=m.artifact_ref,
                artifact_version=m.artifact_version, from_bot=m.owner, to_bot=to_bot,
                outcome="draft ready", requested_action="deliver",
                acceptance_criterion="meets scope")
    base.update(kw)
    return base


def test_roster_matches_design():
    assert validate_roster() == []
    assert len(ROSTER) == 13 and len(GROUPS) == 5


def test_oversized_group_and_uncovered_role_detected():
    groups = dict(GROUPS)
    groups["Direction & Capital"] = ("Strategos", list(ROSTER)[:7])
    groups.pop("Compounding & Continuity")
    problems = validate_roster(groups)
    assert any("exceeds 6" in p for p in problems)


def test_synthetic_mission_end_to_end():
    rec = ControlRecord()
    m = _running(rec)

    rec.claim(m.mission_id, "Concord", 0)                        # Revenue prepares
    v = rec.save_artifact(m.mission_id, "Concord", "artifacts/proposal.md")
    rec.handoff(_packet(m, "Continuum"))                         # -> Delivery
    rec.respond_handoff(m.mission_id, "Continuum", accept=True)
    assert m.owner == "Continuum"

    rec.claim(m.mission_id, "Continuum", v)
    rec.save_artifact(m.mission_id, "Continuum", "artifacts/deliverable-synthetic.md")
    rec.transition(m.mission_id, "REVIEW", by="Continuum")
    rec.review(m.mission_id, "Veritas", criteria_met=True,       # independent acceptance
               claims=[{"claim": "meets scope", "evidence": ["checklist-v2"]}])
    assert m.state == "ACCEPTED"

    rec.transition(m.mission_id, "DELIVERED", by="Continuum")
    rec.record_collection(m.mission_id, 600.0, "synthetic-invoice-001", synthetic=True)
    rec.transition(m.mission_id, "COLLECTED", by="Continuum")   # Aurelius reconciles
    rec.handoff(_packet(m, "Mnemosyne", requested_action="extract reusable SOP"))
    rec.respond_handoff(m.mission_id, "Mnemosyne", accept=True)  # -> Compounding

    assert rec.totals() == {"real_collected_usd": 0.0, "synthetic_collected_usd": 600.0,
                            "execution_authority": False}


class TestSafeFailures:
    def test_missing_artifact(self):
        rec = ControlRecord()
        m = _running(rec)
        with pytest.raises(MissionRefusal, match="missing"):
            rec.handoff(_packet(m, "Continuum", artifact_ref=""))

    def test_stale_artifact_version(self):
        rec = ControlRecord()
        m = _running(rec)
        rec.claim(m.mission_id, "Concord", 0)
        rec.save_artifact(m.mission_id, "Concord", "a.md")
        with pytest.raises(MissionRefusal, match="not the record's current"):
            rec.handoff(_packet(m, "Continuum", artifact_version=0))

    def test_duplicate_claim(self):
        rec = ControlRecord()
        m = _running(rec)
        rec.claim(m.mission_id, "Concord", 0)
        with pytest.raises(MissionRefusal, match="duplicate claim"):
            rec.claim(m.mission_id, "Mythos", 0)

    def test_duplicate_mission(self):
        rec = ControlRecord()
        rec.open(**_contract())
        with pytest.raises(MissionRefusal, match="already exists"):
            rec.open(**_contract())

    def test_incomplete_contract_names_missing_fields(self):
        with pytest.raises(MissionRefusal, match="acceptance_criteria"):
            ControlRecord().open(**_contract(acceptance_criteria=""))

    def test_unsupported_commercial_assertion_rejected_with_repair(self):
        rec = ControlRecord()
        m = _running(rec)
        rec.transition(m.mission_id, "REVIEW", by="Concord")
        rec.review(m.mission_id, "Veritas", criteria_met=True,
                   claims=[{"claim": "buyers will pay $600/month", "evidence": []}],
                   repair="attach a buyer quote or remove the price claim")
        assert m.state == "REJECTED"
        assert m.history[-1]["unsupported"] == ["buyers will pay $600/month"]

    def test_rejection_without_repair_refused(self):
        rec = ControlRecord()
        m = _running(rec)
        rec.transition(m.mission_id, "REVIEW", by="Concord")
        with pytest.raises(MissionRefusal, match="repair path"):
            rec.review(m.mission_id, "Veritas", criteria_met=False, claims=[])

    def test_producer_cannot_self_accept(self):
        rec = ControlRecord()
        m = _running(rec)
        rec.transition(m.mission_id, "REVIEW", by="Concord")
        with pytest.raises(MissionRefusal):
            rec.review(m.mission_id, "Concord", criteria_met=True, claims=[])
        with pytest.raises(MissionRefusal, match="reviewer's verdict"):
            rec.transition(m.mission_id, "ACCEPTED", by="Concord")

    def test_handoff_rejection_must_name_requirement(self):
        rec = ControlRecord()
        m = _running(rec)
        rec.claim(m.mission_id, "Concord", 0)
        rec.save_artifact(m.mission_id, "Concord", "a.md")
        rec.handoff(_packet(m, "Continuum"))
        with pytest.raises(MissionRefusal, match="missing requirement"):
            rec.respond_handoff(m.mission_id, "Continuum", accept=False)
        rec.respond_handoff(m.mission_id, "Continuum", accept=False, reason="no capacity this week")
        assert m.owner == "Concord"

    def test_absent_permission(self):
        rec = ControlRecord()
        m = _running(rec)
        with pytest.raises(MissionRefusal, match="absent permission"):
            rec.authorize_effect(m.mission_id, "send", now=NOW)

    def test_expired_grant(self):
        rec = ControlRecord()
        g = Grant("G-1", frozenset({"send"}), expires_at=NOW - timedelta(minutes=1))
        m = _running(rec, grant=g)
        with pytest.raises(MissionRefusal, match="expired grant"):
            rec.authorize_effect(m.mission_id, "send", now=NOW)

    def test_grant_scope_and_cash_cap(self):
        rec = ControlRecord()
        g = Grant("G-2", frozenset({"send", "spend"}), NOW + timedelta(days=1), cash_cap_usd=50)
        m = _running(rec, grant=g)
        assert rec.authorize_effect(m.mission_id, "send", now=NOW)["execution_authority"] is False
        with pytest.raises(MissionRefusal, match="does not cover 'publish'"):
            rec.authorize_effect(m.mission_id, "publish", now=NOW)
        with pytest.raises(MissionRefusal, match="cash cap"):
            rec.authorize_effect(m.mission_id, "spend", amount_usd=60, now=NOW)

    def test_uncertain_external_result_blocks_instead_of_retrying(self):
        rec = ControlRecord()
        m = _running(rec)
        rec.record_effect_result(m.mission_id, "send", "unknown")
        assert m.state == "BLOCKED"
        assert m.history[-1]["event"] == "reconcile_before_retry"


class TestMoneyAndDecisions:
    def test_collection_needs_evidence(self):
        rec = ControlRecord()
        m = rec.open(**_contract(synthetic=False))
        with pytest.raises(MissionRefusal, match="promise is not cash"):
            rec.record_collection(m.mission_id, 600.0, "", synthetic=False)

    def test_synthetic_never_enters_real_mission(self):
        rec = ControlRecord()
        real = rec.open(**_contract(mission_id="M-REAL", synthetic=False))
        with pytest.raises(MissionRefusal, match="synthetic amounts"):
            rec.record_collection(real.mission_id, 600.0, "x", synthetic=True)
        assert rec.totals()["real_collected_usd"] == 0.0

    def test_commit_requires_accepted_evidence(self):
        rec = ControlRecord()
        m = rec.open(**_contract())
        with pytest.raises(MissionRefusal, match="not encouragement"):
            rec.decide(m.mission_id, "COMMIT", "Hegemony", "looks promising")
        assert rec.decide(m.mission_id, "VALIDATE", "Hegemony", "cheapest buyer test").decision == "VALIDATE"

    def test_unknown_decision_verb_refused(self):
        rec = ControlRecord()
        m = rec.open(**_contract())
        with pytest.raises(MissionRefusal):
            rec.decide(m.mission_id, "LAUNCH", "Hegemony", "go")
