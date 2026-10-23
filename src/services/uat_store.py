"""Durable UAT ledger: the control record and swarm ledger, on disk.

Every accepted operation is appended to one JSON-lines event log and
replayed on open, so the record survives restarts and any agent with a
shell (a Claude agent, a script behind a Grok bot, a person) can use the
same truth:

    python -m src.services.uat_store --db runs/uat/ledger.jsonl <op> '<json>'

Refused operations are never written: an operation is applied to the
in-memory record first and persisted only if it succeeds. Appends hold an
exclusive file lock and fsync, so concurrent writers serialize instead of
interleaving. Read-only ops (status, route, tier, slot_review,
contribution_plan) are not logged.

Nothing here sends, spends, signs or publishes: execution_authority is
False in every result.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone

from .uat_missions import ControlRecord, Grant, MissionRefusal
from .uat_swarm import Agent, Outcome, SwarmLedger, SwarmRefusal

WRITE_OPS = ("register_agent", "open_mission", "transition", "claim", "save_artifact",
             "handoff", "respond_handoff", "review", "decide", "authorize_effect",
             "record_effect_result", "record_collection", "record_outcome")
READ_OPS = ("status", "route", "tier", "slot_review", "contribution_plan")


def _dt(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _plain(obj):
    if is_dataclass(obj):
        return {k: _plain(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_plain(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class UATStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self.record = ControlRecord()
        self.swarm = SwarmLedger()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    if line.strip():
                        event = json.loads(line)
                        try:
                            self._apply(event["op"], event["args"])
                        except (MissionRefusal, SwarmRefusal) as exc:
                            raise RuntimeError(f"ledger corrupt at line {n}: {exc}") from exc

    # -- dispatch -------------------------------------------------------------
    def _apply(self, op: str, a: dict):
        r, s = self.record, self.swarm
        if op == "register_agent":
            return s.register(Agent(**a))
        if op == "open_mission":
            a = dict(a)
            if a.get("grant"):
                g = a["grant"]
                a["grant"] = Grant(g["grant_id"], frozenset(g["actions"]), _dt(g["expires_at"]),
                                   float(g.get("cash_cap_usd", 0.0)))
            return r.open(**a)
        if op == "transition":
            return r.transition(a["mission_id"], a["state"], by=a["by"])
        if op == "claim":
            return r.claim(a["mission_id"], a["bot"], a["artifact_version"])
        if op == "save_artifact":
            return r.save_artifact(a["mission_id"], a["bot"], a["artifact_ref"])
        if op == "handoff":
            return r.handoff(a)
        if op == "respond_handoff":
            return r.respond_handoff(a["mission_id"], a["bot"], a["accept"], a.get("reason", ""))
        if op == "review":
            return r.review(a["mission_id"], a["reviewer"], claims=a.get("claims", []),
                            criteria_met=a["criteria_met"], repair=a.get("repair", ""))
        if op == "decide":
            return r.decide(a["mission_id"], a["verb"], a["by"], a["rationale"])
        if op == "authorize_effect":
            return r.authorize_effect(a["mission_id"], a["action"],
                                      amount_usd=float(a.get("amount_usd", 0)), now=_dt(a.get("now")))
        if op == "record_effect_result":
            return r.record_effect_result(a["mission_id"], a["action"], a["status"])
        if op == "record_collection":
            return r.record_collection(a["mission_id"], float(a["amount_usd"]),
                                       a.get("evidence_ref", ""), synthetic=bool(a["synthetic"]))
        if op == "record_outcome":
            a = dict(a, at=_dt(a.get("at")))
            return s.record(Outcome(**a))
        raise ValueError(f"unknown write op {op!r}")

    def _read(self, op: str, a: dict):
        now = _dt(a.get("now"))
        if op == "status":
            return {"missions": {m.mission_id: {"state": m.state, "owner": m.owner,
                                                "decision": m.decision, "synthetic": m.synthetic}
                                 for m in self.record.missions.values()},
                    "agents": sorted(self.swarm.agents), **self.record.totals()}
        if op == "route":
            return self.swarm.route(a["mission_id"], a["stage"], a["slot"], now, a.get("active"))
        if op == "tier":
            return self.swarm.tier(a["agent_id"], a["stage"], now)
        if op == "slot_review":
            return self.swarm.slot_review(now)
        if op == "contribution_plan":
            return self.swarm.contribution_plan(a["mission_id"], float(a["distributable_usd"]))
        raise ValueError(f"unknown read op {op!r}")

    # -- public ---------------------------------------------------------------
    def execute(self, op: str, args: dict) -> dict:
        if op in READ_OPS:
            return {"ok": True, "result": _plain(self._read(op, args)), "execution_authority": False}
        if op not in WRITE_OPS:
            raise ValueError(f"unknown op {op!r}; write ops {WRITE_OPS}, read ops {READ_OPS}")
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                result = self._apply(op, args)       # refuses before anything is written
                event = {"op": op, "args": _plain(args),
                         "at": datetime.now(timezone.utc).isoformat()}
                fh.write(json.dumps(event, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
        return {"ok": True, "result": _plain(result), "execution_authority": False}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="uat_store", description=__doc__.splitlines()[0])
    p.add_argument("--db", default="runs/uat/ledger.jsonl")
    p.add_argument("op", choices=WRITE_OPS + READ_OPS)
    p.add_argument("args", nargs="?", default="{}", help="JSON object of arguments")
    ns = p.parse_args(argv)
    try:
        out = UATStore(ns.db).execute(ns.op, json.loads(ns.args))
    except (MissionRefusal, SwarmRefusal, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "refused": str(exc), "execution_authority": False}))
        return 1
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
