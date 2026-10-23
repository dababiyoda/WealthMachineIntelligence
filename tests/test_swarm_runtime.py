"""UAT swarm runtime tests (scripted models; no network, no spend).

A full cycle lands every stage in the durable ledger, routes red-team
review to a different lineage when one exists, keeps going when one
mission fails, stops at the budget, honours the kill switch and resumes
without repaying for finished work.
"""
import json

import pytest

from src.services.uat_store import UATStore
from src.swarm import ModelError, RuntimeConfig, ScriptedClient, SwarmPaused, SwarmRuntime
from src.swarm.__main__ import _ingest
from src.swarm.runtime import _slug

SRC = [{"url": "https://a.example/1", "claim": "x"}, {"url": "https://b.example/2", "claim": "y"}]


def script(fail_on=None, dead=()):
    def respond(system, task):
        role = system.split("ROLE: ", 1)[1].split(" ", 1)[0]
        name = "dead-idea" if any(d in task for d in dead) else "live"
        if fail_on and fail_on in task and role == "Logos":
            raise ModelError("model declined (category=None)")
        return {
            "Prometheus": {"opportunities": [
                {"name": n, "one_liner": n, "buyer": "clinics", "recurring_paid_problem": "p",
                 "edge": "speed", "why_now": "now", "evidence": SRC}
                for n in ("Audit Prep Kits", "Dead Idea", "Grant Briefs")]},
            "Logos": {"verdict": "not_viable" if name == "dead-idea" else "viable",
                      "demand_evidence": SRC, "competitors": [], "price_anchor_usd": 500,
                      "notes": "n"},
            "Veritas": {"refuted": False, "severity": "low", "argument": "", "evidence": []},
            "Aegis": ({"refuted": False, "severity": "low", "argument": "", "evidence": []}
                      if "Diligence" in task else
                      {"flags": [], "notes": ""}),
            "Strategos": {"refuted": False, "severity": "low", "argument": "", "evidence": []},
            "Daedalus": {"title": "Kit", "deliverable": "d", "price_usd": 500, "unit_cost_usd": 50,
                         "delivery_days": 7, "refundable": True, "tools": [],
                         "differentiation": "", "expansion_paths": []},
            "Aurelius": {"max_loss_usd": 0, "expected_paid_commitments_14d": 2, "fermi": "",
                         "kill_rules": ["<2 paid in 14d"]},
            "Concord": {"buyer_profile": "", "positioning": "", "outreach_drafts": [],
                        "conversation_script": [],
                        "actions": [{"type": "contact", "description": "email 10 clinics"}]},
        }[role]
    return respond


def _runtime(tmp_path, clients, **cfg):
    store = UATStore(str(tmp_path / "ledger.jsonl"))
    return store, SwarmRuntime(store, clients, RuntimeConfig(out_dir=str(tmp_path / "out"), **cfg))


def test_full_cycle_lands_in_ledger(tmp_path):
    store, rt = _runtime(tmp_path, [ScriptedClient("claude", script(dead=("Dead Idea",)))])
    out = rt.run_cycle("c1", "test focus")
    missions = store.record.missions
    assert set(out["missions"]) == {"c1:audit-prep-kits", "c1:dead-idea", "c1:grant-briefs"}
    assert missions["c1:audit-prep-kits"].decision == "VALIDATE"
    assert missions["c1:dead-idea"].decision == "KILL"
    assert out["ranked_go"] and out["execution_authority"] is False
    brief = open(out["brief_path"]).read()
    assert "[contact]" in brief and "Nothing was sent" in brief
    # reopen from disk: the whole cycle is durable
    again = UATStore(str(tmp_path / "ledger.jsonl"))
    assert again.record.missions["c1:dead-idea"].decision == "KILL"
    assert any(o.stage == "offer" for o in again.swarm.outcomes)


def test_red_team_routes_to_other_lineage(tmp_path):
    a = ScriptedClient("claude", script())
    b = ScriptedClient("grok", script())
    store, rt = _runtime(tmp_path, [a, b], max_opportunities=1)
    rt.run_cycle("c2", "f")
    red = [o for o in store.swarm.outcomes if o.stage.startswith("red_")]
    diligence = next(o for o in store.swarm.outcomes if o.stage == "diligence")
    producer = store.swarm.agents[diligence.agent_id].lineage
    assert red and all(store.swarm.agents[o.agent_id].lineage != producer for o in red)


def test_one_failing_mission_does_not_stop_cycle(tmp_path):
    store, rt = _runtime(tmp_path, [ScriptedClient("claude", script(fail_on="Grant Briefs"))])
    out = rt.run_cycle("c3", "f")
    assert [b["mission_id"] for b in out["blocked"]] == ["c3:grant-briefs"]
    assert store.record.missions["c3:grant-briefs"].state == "BLOCKED"
    assert store.record.missions["c3:audit-prep-kits"].decision == "VALIDATE"


def test_budget_stops_cycle(tmp_path):
    store, rt = _runtime(tmp_path, [ScriptedClient("claude", script(), cost_usd=1.0)],
                         cycle_budget_usd=5.0)
    out = rt.run_cycle("c4", "f")
    assert out["stopped"] and "budget" in out["stopped"]
    assert out["spent_usd"] <= 6.0


def test_kill_switch(tmp_path, monkeypatch):
    _, rt = _runtime(tmp_path, [ScriptedClient("claude", script())])
    monkeypatch.setenv("UAT_SWARM_PAUSED", "1")
    with pytest.raises(SwarmPaused):
        rt.run_cycle("c5", "f")


def test_resume_does_not_repay(tmp_path):
    client = ScriptedClient("claude", script())
    _, rt = _runtime(tmp_path, [client])
    rt.run_cycle("c6", "f")
    calls = len(client.calls)
    rt.run_cycle("c6", "f")
    assert len(client.calls) == calls            # scout cached, missions skipped


def test_ingest_workflow_dossier(tmp_path):
    dossier = {"policy": {"loss_cap_usd": 0}, "opportunities": [{
        "name": "x", "network_edge": False, "evidence": SRC, "red_team": [],
        "offer": {"price_usd": 500, "unit_cost_usd": 50, "delivery_days": 7},
        "finance": {"max_loss_usd": 0, "expected_paid_commitments_14d": 1},
        "legal": {"flags": []}, "actions": []}]}
    path = tmp_path / "live-run-dossier.json"
    path.write_text(json.dumps(dossier))
    store = UATStore(str(tmp_path / "ledger.jsonl"))
    out = _ingest(store, str(path), str(tmp_path / "out"))
    assert out["ingested"] == [{"mission_id": "live-run:x", "decision": "VALIDATE"}]
    assert "VALIDATE" in open(out["brief_path"]).read()
    assert _ingest(store, str(path), str(tmp_path / "out"))["ingested"] == []   # idempotent
    handoff = tmp_path / "wf-output.json"                      # workflow output file shape
    handoff.write_text(json.dumps({"summary": "s", "result": {"run_label": "wf", "dossier": dossier,
                                                                "full": []}}))
    assert _ingest(store, str(handoff), str(tmp_path / "out"))["ingested"][0]["mission_id"] == "wf:x"
    assert _slug("A b!") == "a-b"
