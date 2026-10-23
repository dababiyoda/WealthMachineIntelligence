"""Command line for the UAT swarm.

    python -m src.swarm run --focus "..." [--run-id ID] [--budget 25] [--max-opps 4]
    python -m src.swarm status
    python -m src.swarm ingest runs/uat/<label>-dossier.json

`run` needs Anthropic credentials (ANTHROPIC_API_KEY or an `ant auth login`
profile). `ingest` brings a Claude Code workflow run into the same ledger.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from src.services.uat_governor import govern
from src.services.uat_store import UATStore

from .runtime import BudgetExceeded, RuntimeConfig, SwarmPaused, SwarmRuntime, _slug


def _load_handoff(path: str) -> tuple[str, dict, list]:
    """Accept a bare dossier, a workflow hand-off, or a workflow output file."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data = data.get("result", data) if isinstance(data.get("result"), dict) else data
    if "dossier" in data:
        return _slug(data.get("run_label", "workflow")), data["dossier"], data.get("full", [])
    run = _slug(os.path.basename(path).replace("-dossier.json", "").replace(".json", ""))
    return run, data, []


def _write_brief(run: str, gov: dict, full: list, out_dir: str) -> str:
    by_name = {f["name"]: f for f in full}
    lines = [f"# UAT cycle {run}", "",
             "Authority: research and drafts only. Nothing was sent, spent, signed or published.", "",
             f"Decisions: {gov['counts']}", "", "## VALIDATE (bounded buyer test, awaiting Alfonso)", ""]
    for name in gov["ranked_go"] or []:
        offer = (by_name.get(name) or {}).get("offer") or {}
        lines.append(f"- **{name}**: {offer.get('title', '')} at ${offer.get('price_usd', 0):,.0f}")
    if not gov["ranked_go"]:
        lines.append("None this cycle.")
    lines += ["", "## Per opportunity", ""]
    for d in gov["decisions"]:
        f = by_name.get(d["name"], {})
        offer = f.get("offer") or {}
        lines += [f"### {d['decision_verb']}: {d['name']}",
                  f"- Buyer: {(f.get('scout') or {}).get('buyer', '')}",
                  f"- Offer: {offer.get('title', '(not designed)')}"
                  + (f" at ${offer['price_usd']:,.0f}, margin {d['gross_margin']:.0%}" if offer else ""),
                  f"- Projected net 30d: ${d['projected_net_30d_usd']:,.0f}",
                  "- Reasons:"] + [f"  - {r}" for r in d["reasons"]] + [""]
    lines += ["## Human decision queue", ""]
    lines += [f"- [{q['type']}] {q['opportunity']}: {q['description']}"
              for q in gov["human_decision_queue"]] or ["- (empty)"]
    path = os.path.join(out_dir, f"{run}-brief.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def _ingest(store: UATStore, path: str, out_dir: str = "runs/uat") -> dict:
    run, dossier, full = _load_handoff(path)
    os.makedirs(out_dir, exist_ok=True)
    gov = govern(dossier)
    with open(os.path.join(out_dir, f"{run}-dossier.json"), "w", encoding="utf-8") as fh:
        json.dump(dossier, fh, indent=2)
    with open(os.path.join(out_dir, f"{run}-governor.json"), "w", encoding="utf-8") as fh:
        json.dump(gov, fh, indent=2)
    now = datetime.now(timezone.utc)
    added = []
    for verdict, opp in zip(gov["decisions"], dossier["opportunities"]):
        mission_id = f"{run}:{_slug(opp['name'])}"
        if mission_id in store.record.missions:
            continue
        ex = store.execute
        ex("open_mission", {"mission_id": mission_id, "venture_id": _slug(opp["name"]),
                            "owner": "Logos", "reviewer": "Veritas",
                            "bounded_outcome": f"decision-ready dossier: {opp['name']}",
                            "active_bottleneck": "first paid commitment",
                            "acceptance_criteria": "governor gates pass with >=2 independent sources",
                            "deadline": now.isoformat(), "origin_group": "Opportunity Foundry"})
        for state in ("SCOPED", "AUTHORIZED", "READY", "RUNNING", "REVIEW"):
            ex("transition", {"mission_id": mission_id, "state": state, "by": "Logos"})
        urls = [e.get("url") for e in opp.get("evidence", []) if e.get("url")]
        ex("review", {"mission_id": mission_id, "reviewer": "Veritas",
                      "claims": [{"claim": f"demand for {opp['name']}", "evidence": urls}],
                      "criteria_met": verdict["decision"] == "GO",
                      "repair": "; ".join(verdict["reasons"])})
        ex("decide", {"mission_id": mission_id, "verb": verdict["decision_verb"], "by": "Hegemony",
                      "rationale": "; ".join(verdict["reasons"])})
        added.append({"mission_id": mission_id, "decision": verdict["decision_verb"]})
    brief = _write_brief(run, gov, full, out_dir)
    return {"ingested": added, "counts": gov["counts"], "brief_path": brief,
            "execution_authority": False}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m src.swarm")
    p.add_argument("--db", default=os.getenv("UAT_LEDGER_PATH", "runs/uat/ledger.jsonl"))
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--focus", required=True)
    r.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("cycle-%Y%m%d-%H%M"))
    r.add_argument("--budget", type=float, default=float(os.getenv("UAT_CYCLE_BUDGET_USD", "25")))
    r.add_argument("--max-opps", type=int, default=4)
    r.add_argument("--model", default=os.getenv("UAT_MODEL", "claude-opus-5-5"))
    r.add_argument("--out", default=os.getenv("UAT_OUT_DIR", "runs/uat"))
    sub.add_parser("status")
    i = sub.add_parser("ingest", help="dossier, workflow hand-off, or workflow output file")
    i.add_argument("dossier")
    i.add_argument("--out", default=os.getenv("UAT_OUT_DIR", "runs/uat"))
    ns = p.parse_args(argv)

    store = UATStore(ns.db)
    if ns.cmd == "status":
        print(json.dumps(store.execute("status", {}), indent=2))
        return 0
    if ns.cmd == "ingest":
        print(json.dumps(_ingest(store, ns.dossier, ns.out), indent=2))
        return 0

    from .model import ClaudeClient
    runtime = SwarmRuntime(store, [ClaudeClient(model=ns.model)],
                           RuntimeConfig(max_opportunities=ns.max_opps, cycle_budget_usd=ns.budget,
                                         out_dir=ns.out))
    try:
        result = runtime.run_cycle(ns.run_id, ns.focus)
    except (SwarmPaused, BudgetExceeded) as exc:
        print(json.dumps({"ok": False, "stopped": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
