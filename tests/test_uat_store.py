"""Durable UAT ledger tests: survives restart, never writes a refusal."""
import json

import pytest

from src.services.uat_missions import MissionRefusal
from src.services.uat_store import UATStore, main

MISSION = dict(mission_id="M-1", venture_id="V-1", owner="Concord", reviewer="Veritas",
               bounded_outcome="pilot reply", active_bottleneck="first paid commitment",
               acceptance_criteria="scope and price stated", deadline="2026-11-01")


def _lines(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def test_state_survives_reopen(tmp_path):
    db = tmp_path / "ledger.jsonl"
    s = UATStore(str(db))
    s.execute("register_agent", {"agent_id": "concord-grok", "slot": "Concord", "lineage": "grok",
                                 "principal": "Alfonso"})
    s.execute("open_mission", dict(MISSION, grant={"grant_id": "G1", "actions": ["send"],
                                                   "expires_at": "2026-12-01T00:00:00+00:00"}))
    s.execute("transition", {"mission_id": "M-1", "state": "SCOPED", "by": "Concord"})
    s.execute("record_outcome", {"agent_id": "concord-grok", "mission_id": "M-1", "stage": "reply",
                                 "accepted": True, "grade": "external",
                                 "reviewer_id": "external:buyer", "at": "2026-10-22T12:00:00+00:00"})

    again = UATStore(str(db))
    assert again.record.missions["M-1"].state == "SCOPED"
    assert again.record.missions["M-1"].grant.actions == frozenset({"send"})
    tier = again.execute("tier", {"agent_id": "concord-grok", "stage": "reply",
                                  "now": "2026-10-23T00:00:00+00:00"})
    assert tier["result"]["external"] == 1
    assert len(_lines(db)) == 4                     # read ops are not logged


def test_refused_operation_is_not_written(tmp_path):
    db = tmp_path / "ledger.jsonl"
    s = UATStore(str(db))
    s.execute("open_mission", MISSION)
    with pytest.raises(MissionRefusal):
        s.execute("transition", {"mission_id": "M-1", "state": "COLLECTED", "by": "Concord"})
    assert [e["op"] for e in _lines(db)] == ["open_mission"]
    assert UATStore(str(db)).record.missions["M-1"].state == "PROPOSED"


def test_cli_round_trip_and_refusal(tmp_path, capsys):
    db = str(tmp_path / "ledger.jsonl")
    assert main(["--db", db, "open_mission", json.dumps(MISSION)]) == 0
    capsys.readouterr()
    assert main(["--db", db, "record_collection",
                 json.dumps({"mission_id": "M-1", "amount_usd": 600, "synthetic": False})]) == 1
    assert "promise is not cash" in json.loads(capsys.readouterr().out)["refused"]
    assert main(["--db", db, "status"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["result"]["real_collected_usd"] == 0 and out["execution_authority"] is False
