"""Keep every idea: hand non-GO opportunities to RailScout for the Idea Refinery.

A KILL, PARK or RECONFIGURE is a verdict on one design at one moment, not
on the underlying failure. Each one is converted into a Kernel-valid
OpportunityPacket (the wire both RailScout and the DALEOBANKS Idea
Refinery speak) plus a research request naming exactly what RailScout must
find before the idea is worth another cycle. Packets are written to an
outbox; delivery to RailScout is a separate, authorised step.

Packet ids are deterministic per (run, opportunity), so re-running the
hand-off never duplicates an idea.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from adapters.contract_validation import validate_contract

CREATED_BY = "spiffe://uniimente.internal/wealthmachine/uat"
NAMESPACE = uuid.UUID("5b1e7d2c-3a8f-4c61-9e0b-7f2d4a6c8e10")


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _packet(run: str, decision: dict, opp: dict, full: dict, now: datetime) -> dict:
    scout = full.get("scout") or {}
    offer = full.get("offer") or {}
    finance = full.get("finance") or {}
    red = full.get("red") or []
    buyer = scout.get("buyer") or "unidentified buyer"
    reasons = decision.get("reasons") or ["no reason recorded"]
    risks = [r.get("argument", "")[:400] for r in red if r.get("refuted")] + reasons
    packet = {
        "packet_id": str(uuid.uuid5(NAMESPACE, f"{run}:{decision['name']}")),
        "schema_version": "1.0",
        "created_by": CREATED_BY,
        "created_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observed_failure": scout.get("recurring_paid_problem") or decision["name"],
        "affected_actors": [buyer],
        "pain_owner": buyer,
        "budget_owner": buyer,
        "governing_bottleneck": reasons[0][:1000],
        "missing_proof": "; ".join(reasons)[:2000],
        "smallest_intervention": offer.get("title") or "not yet designed",
        "cheapest_decisive_test": ("; ".join(finance.get("kill_rules", []))
                                   or "find one paying buyer under the cash cap")[:1000],
        "possible_business_form": "Service",
        "capital_requirement_usd": 0,
        "key_risks": [r for r in risks if r][:10] or ["unassessed"],
        "wedge_to_control_path": scout.get("edge") or scout.get("access_edge") or "unstated",
        "evidence_refs": sorted({_sha(e["url"]) for e in opp.get("evidence", []) if e.get("url")}),
    }
    return validate_contract(packet, "opportunity-packet")


def handoff(run: str, gov: dict, dossier: dict, full: list, out_dir: str,
            now: datetime | None = None, unreviewed: list | None = None) -> dict:
    """Write one packet + research request per non-GO idea; return the index.

    unreviewed: scouted ideas the cycle had no capacity to validate; they are
    kept too, marked UNREVIEWED.
    """
    now = now or datetime.now(timezone.utc)
    by_name = {f["name"]: f for f in full}
    opps = {o["name"]: o for o in dossier["opportunities"]}
    gov = dict(gov, decisions=list(gov["decisions"]))
    for scout in unreviewed or []:
        name = scout["name"]
        if name in opps:
            continue
        by_name[name] = {"name": name, "scout": scout}
        opps[name] = {"name": name, "evidence": scout.get("evidence", [])}
        gov["decisions"].append({"name": name, "decision": "UNREVIEWED",
                                 "decision_verb": "UNREVIEWED",
                                 "reasons": ["scouted but not yet validated (cycle capacity)"]})
    outbox = os.path.join(out_dir, "railscout-outbox", run)
    os.makedirs(outbox, exist_ok=True)
    index = []
    for d in gov["decisions"]:
        if d["decision"] == "GO":
            continue
        packet = _packet(run, d, opps.get(d["name"], {}), by_name.get(d["name"], {}), now)
        request = {
            "packet_id": packet["packet_id"], "idea": d["name"], "verdict": d["decision_verb"],
            "route": "RailScout -> Idea Refinery (DALEOBANKS) -> WealthMachine",
            "research_questions": [f"Resolve or route around: {r}" for r in d["reasons"]]
            + ["Find the strongest existing competitor and its price.",
               "Find one buyer segment for whom this blocker does not apply."],
            "packet": packet, "execution_authority": False,
        }
        path = os.path.join(outbox, f"{d['name']}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(request, fh, indent=2)
        index.append({"idea": d["name"], "verdict": d["decision_verb"],
                      "packet_id": packet["packet_id"], "path": path})
    with open(os.path.join(outbox, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)
    return {"outbox": outbox, "kept": index, "execution_authority": False}
