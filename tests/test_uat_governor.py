"""UAT governor tests: the deterministic gate over the all-agent workflow.

Agents propose; the governor decides from fixed rules. Unverified or
red-team-refuted ideas die, over-cap or slow offers rework, legal blockers
and passive capital hold for counsel, and nothing ever gains execution
authority.
"""
import json

import pytest

from src.services.uat_governor import (GO, HOLD, KILL, REWORK, GovernorRefusal,
                                       govern, main)


def _opp(**kw):
    base = dict(
        name="bookkeeping-cleanup-for-trades",
        network_edge=True,
        evidence=[{"url": "https://a.example/1"}, {"url": "https://b.example/2"}],
        red_team=[{"lens": "market", "refuted": False},
                  {"lens": "legal", "refuted": False},
                  {"lens": "people", "refuted": False}],
        offer={"price_usd": 600.0, "unit_cost_usd": 150.0, "delivery_days": 10},
        finance={"max_loss_usd": 300.0, "expected_paid_commitments_14d": 3},
        legal={"flags": []},
        actions=[{"type": "contact", "description": "pitch 10 contractors"},
                 {"type": "research", "description": "read reviews"}],
    )
    base.update(kw)
    return base


def _decide(**kw):
    return govern({"opportunities": [_opp(**kw)]})["decisions"][0]


class TestGates:
    def test_clean_opportunity_goes_to_human_queue(self):
        out = govern({"opportunities": [_opp()]})
        assert out["decisions"][0]["decision"] == GO
        assert out["ranked_go"] == ["bookkeeping-cleanup-for-trades"]
        assert [q["type"] for q in out["human_decision_queue"]] == ["contact"]
        assert all(q["requires_human_approval"] for q in out["human_decision_queue"])

    def test_unverified_killed(self):
        assert _decide(evidence=[{"url": "https://a.example/1"}])["decision"] == KILL

    def test_duplicate_sources_count_once(self):
        dup = [{"url": "https://a.example/1"}, {"url": "https://a.example/1"}]
        assert _decide(evidence=dup)["decision"] == KILL

    def test_two_refutations_kill(self):
        rt = [{"lens": "market", "refuted": True}, {"lens": "people", "refuted": True}]
        assert _decide(red_team=rt)["decision"] == KILL

    def test_single_critical_refutation_kills(self):
        rt = [{"lens": "legal", "refuted": True, "severity": "critical"}]
        assert _decide(red_team=rt)["decision"] == KILL

    def test_over_loss_cap_reworks(self):
        d = _decide(finance={"max_loss_usd": 5000.0})
        assert d["decision"] == REWORK and "exceeds cap" in d["reasons"][0]

    def test_unknown_loss_reworks(self):
        assert _decide(finance={})["decision"] == REWORK

    def test_slow_delivery_reworks(self):
        offer = {"price_usd": 600.0, "unit_cost_usd": 150.0, "delivery_days": 90}
        assert _decide(offer=offer)["decision"] == REWORK

    def test_thin_margin_reworks(self):
        offer = {"price_usd": 100.0, "unit_cost_usd": 90.0, "delivery_days": 5}
        assert _decide(offer=offer)["decision"] == REWORK

    def test_blocking_legal_flag_holds(self):
        legal = {"flags": [{"issue": "contractor license required", "blocking": True}]}
        assert _decide(legal=legal)["decision"] == HOLD

    def test_passive_capital_always_holds(self):
        acts = [{"type": "raise_capital", "description": "friends and family round"}]
        d = _decide(actions=acts)
        assert d["decision"] == HOLD
        assert d["human_queue"][0]["type"] == "raise_capital"

    def test_killed_ideas_queue_nothing(self):
        assert _decide(evidence=[])["human_queue"] == []


class TestRankingAndAuthority:
    def test_network_edge_ranks_first_at_equal_economics(self):
        out = govern({"opportunities": [_opp(name="cold", network_edge=False),
                                        _opp(name="warm", network_edge=True)]})
        assert out["ranked_go"] == ["warm", "cold"]

    def test_decision_verbs_never_commit(self):
        out = govern({"opportunities": [_opp(name="go"), _opp(name="dead", evidence=[])]})
        verbs = {d["name"]: d["decision_verb"] for d in out["decisions"]}
        assert verbs == {"go": "VALIDATE", "dead": "KILL"}

    def test_authority_is_never_granted(self):
        out = govern({"opportunities": [_opp()]})
        assert out["execution_authority"] is False
        assert out["requires_human_approval"] is True

    def test_invalid_policy_refuses(self):
        with pytest.raises(GovernorRefusal, match="loss cap"):
            govern({"policy": {"loss_cap_usd": -1}, "opportunities": []})

    def test_malformed_dossier_refuses(self):
        with pytest.raises(GovernorRefusal):
            govern({"ideas": []})


def test_cli_round_trip(tmp_path, capsys):
    path = tmp_path / "dossier.json"
    path.write_text(json.dumps({"policy": {"loss_cap_usd": 250},
                                "opportunities": [_opp()]}))
    assert main(["uat_governor", str(path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decisions"][0]["decision"] == REWORK      # $300 loss > $250 cap
