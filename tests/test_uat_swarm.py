"""Earned-authority swarm tests.

Trust, routing and reward all come from one record of independently
accepted work: same-family review earns nothing, synthetic work earns
nothing, rejections contract autonomy at once, reciprocal vouching is
discounted, new agents still get explored, and no tier ever grants an
external effect.
"""
from datetime import timedelta

import pytest

from src.services.uat_swarm import Agent, Outcome, SwarmLedger, SwarmRefusal, utc

NOW = utc(2026, 10, 23, 12)


def _ledger():
    led = SwarmLedger()
    for a in (Agent("concord-grok", "Concord", "grok", "Alfonso"),
              Agent("concord-claude", "Concord", "claude", "Maria"),
              Agent("veritas-grok", "Veritas", "grok", "UAT"),
              Agent("veritas-claude", "Veritas", "claude", "UAT")):
        led.register(a)
    return led


def _win(led, agent, reviewer, grade="independent", days_ago=1, mission="M1", accepted=True, **kw):
    return led.record(Outcome(agent, mission, "proposal", accepted, grade, reviewer,
                              at=NOW - timedelta(days=days_ago), **kw))


class TestProofGrading:
    def test_same_lineage_review_earns_nothing(self):
        led = _ledger()
        _win(led, "concord-grok", "veritas-grok")
        assert led.standing("concord-grok", "proposal", NOW)["score"] == 0

    def test_cross_lineage_review_earns(self):
        led = _ledger()
        _win(led, "concord-grok", "veritas-claude")
        assert led.standing("concord-grok", "proposal", NOW)["score"] > 0

    def test_only_outside_actor_confers_external(self):
        led = _ledger()
        o = _win(led, "concord-grok", "veritas-claude", grade="external")
        assert led.effective_grade(o) == "independent"
        o2 = _win(led, "concord-grok", "external:buyer-signed-scope", grade="external")
        assert led.effective_grade(o2) == "external"

    def test_synthetic_work_earns_nothing(self):
        led = _ledger()
        _win(led, "concord-grok", "external:demo", grade="external", synthetic=True)
        assert led.standing("concord-grok", "proposal", NOW)["evidence"] == 0

    def test_self_review_and_same_member_review_refused(self):
        led = _ledger()
        led.register(Agent("mythos-maria", "Mythos", "grok", "Maria"))
        with pytest.raises(SwarmRefusal, match="own work"):
            _win(led, "concord-grok", "concord-grok")
        with pytest.raises(SwarmRefusal, match="member's agents"):
            _win(led, "concord-claude", "mythos-maria")


class TestEarnedAutonomy:
    def test_new_agent_starts_on_full_review(self):
        t = _ledger().tier("concord-grok", "proposal", NOW)
        assert t["tier"] == "T0-probation" and t["review_sample_rate"] == 1.0
        assert t["grants_external_authority"] is False

    def test_external_acceptance_earns_less_review(self):
        led = _ledger()
        for i in range(2):
            _win(led, "concord-grok", "external:buyer", grade="external", mission=f"M{i}")
        t = led.tier("concord-grok", "proposal", NOW)
        assert t["tier"] == "T1-trusted" and t["review_sample_rate"] == 0.5

    def test_rejection_contracts_immediately(self):
        led = _ledger()
        for i in range(6):
            _win(led, "concord-grok", "external:buyer", grade="external", mission=f"M{i}")
        assert led.tier("concord-grok", "proposal", NOW)["tier"] == "T2-proven"
        _win(led, "concord-grok", "veritas-claude", accepted=False, mission="M9")
        assert led.tier("concord-grok", "proposal", NOW)["tier"] == "T1-trusted"

    def test_standing_decays(self):
        led = _ledger()
        _win(led, "concord-grok", "external:buyer", grade="external", days_ago=0)
        fresh = led.standing("concord-grok", "proposal", NOW)["score"]
        later = led.standing("concord-grok", "proposal", NOW + timedelta(days=60))["score"]
        assert later == pytest.approx(fresh / 4, rel=0.01)

    def test_reciprocal_vouching_discounted(self):
        led = _ledger()
        _win(led, "concord-grok", "concord-claude")
        before = led.standing("concord-grok", "proposal", NOW)["score"]
        _win(led, "concord-claude", "concord-grok")
        after = led.standing("concord-grok", "proposal", NOW)["score"]
        assert after == pytest.approx(before / 2, abs=0.001)


class TestRouting:
    def test_best_record_wins_and_capacity_respected(self):
        led = _ledger()
        _win(led, "concord-claude", "external:buyer", grade="external")
        missions = [f"route-{i}" for i in range(20)]
        picks = [led.route(m, "proposal", "Concord", NOW)["agent_id"] for m in missions]
        assert picks.count("concord-claude") > picks.count("concord-grok") > 0  # explored too
        r = led.route("route-x", "proposal", "Concord", NOW, active={"concord-claude": 2})
        assert r["agent_id"] == "concord-grok"
        assert r["execution_authority"] is False

    def test_no_capacity_refuses(self):
        led = _ledger()
        with pytest.raises(SwarmRefusal, match="no eligible agent"):
            led.route("m", "proposal", "Concord", NOW,
                      active={"concord-grok": 1, "concord-claude": 1})


class TestSettlementAndSelection:
    def test_contribution_plan_pays_principals_of_proven_work(self):
        led = _ledger()
        _win(led, "concord-claude", "veritas-grok", mission="PAID")        # Maria's agent
        _win(led, "concord-grok", "veritas-grok", mission="PAID")          # same lineage: no credit
        plan = led.contribution_plan("PAID", 1000.0)
        assert plan["shares"] == {"Maria": 800.0, "UAT": 200.0}
        assert plan["requires_human_approval"] and not plan["execution_authority"]

    def test_slot_review_flags_unproven_activity(self):
        led = _ledger()
        _win(led, "concord-grok", "veritas-grok", cost_usd=4.0, founder_minutes=10)
        report = led.slot_review(NOW)
        assert report["Concord"]["verdict"] == "MERGE-OR-PAUSE"
        assert report["Veritas"]["verdict"] == "DORMANT"
