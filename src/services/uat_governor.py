"""UAT governor — the deterministic gate for the all-agent master-plan workflow.

The Universally Adaptive Team's eight roles run as agents
(`.claude/workflows/uat-income-loop.js`). Agents research, argue and draft;
they never decide their own fate. This module does, from the dossier the
agents produce, with rules fixed in advance
(docs/MASTER_PLAN_EFFECT_COMPILATION.md):

    unverified (no sources)               -> KILL
    red team: >=2 refutations, or any
      critical refutation                 -> KILL
    worst-case loss above the loss cap    -> REWORK
    delivery longer than the time box     -> REWORK
    gross margin below the floor          -> REWORK
    blocking legal flag / passive capital -> HOLD_FOR_COUNSEL
    otherwise                             -> GO (to Alfonso's decision queue)

Single Bottleneck Metric: verified net cash collected from paying customers
of network-sourced offers, trailing 30 days. Every GO is ranked by its
projected contribution to it per dollar of worst-case loss.

Hard invariants:
  - execution_authority is hardcoded False: a GO is a proposal, not a launch
  - every consequential action (contact, spend, sign, publish, collect,
    raise capital, form entity) lands in the human decision queue
  - raising money from people who will not work in the venture always
    holds for counsel (Howey investment-contract exposure)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

SBM = ("verified net cash collected from paying customers of "
       "network-sourced offers, trailing 30 days")

CONSEQUENTIAL_ACTIONS = frozenset({
    "contact", "spend", "sign", "publish", "collect_payment",
    "raise_capital", "form_entity",
})

GO, REWORK, KILL, HOLD = "GO", "REWORK", "KILL", "HOLD_FOR_COUNSEL"

# Direction & Capital's decision vocabulary (uat_missions.DECISIONS). A gate
# pass earns only VALIDATE — the cheapest buyer test — never COMMIT, which
# needs accepted external evidence.
DECISION_VERB = {GO: "VALIDATE", REWORK: "RECONFIGURE", KILL: "KILL", HOLD: "PARK"}


class GovernorRefusal(ValueError):
    """The dossier or policy is inadmissible. Fails closed."""


@dataclass
class Policy:
    loss_cap_usd: float = 500.0            # worst-case cash loss per experiment
    timebox_days: int = 30                 # first paid delivery inside this window
    min_gross_margin: float = 0.40
    min_sources: int = 2                   # independent evidence URLs required

    def validate(self) -> list[str]:
        problems = []
        if self.loss_cap_usd < 0:
            problems.append("loss cap may not be negative")
        if self.timebox_days <= 0:
            problems.append("time box must be positive")
        if not 0.0 <= self.min_gross_margin < 1.0:
            problems.append(f"min_gross_margin out of [0,1): {self.min_gross_margin}")
        if self.min_sources < 1:
            problems.append("at least one evidence source is always required")
        return problems


def _num(opp: dict, *path, default=0.0) -> float:
    node = opp
    for key in path:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
    try:
        return float(node)
    except (TypeError, ValueError):
        return default


def assess(opp: dict, policy: Policy) -> dict:
    """Return one opportunity's decision with named reasons."""
    name = str(opp.get("name") or opp.get("id") or "unnamed")
    kill, rework, hold = [], [], []

    sources = {e.get("url") for e in opp.get("evidence", [])
               if isinstance(e, dict) and e.get("url")}
    if len(sources) < policy.min_sources:
        kill.append(f"unverified: {len(sources)} distinct sources < {policy.min_sources}")

    refuted = [r for r in opp.get("red_team", []) if r.get("refuted")]
    if len(refuted) >= 2:
        kill.append(f"red team refuted {len(refuted)} lenses: "
                    + ", ".join(str(r.get("lens")) for r in refuted))
    elif any(r.get("severity") == "critical" for r in refuted):
        kill.append(f"critical refutation: {refuted[0].get('lens')}")

    price = _num(opp, "offer", "price_usd")
    unit_cost = _num(opp, "offer", "unit_cost_usd")
    margin = (price - unit_cost) / price if price > 0 else 0.0
    if price <= 0:
        rework.append("offer has no price; a free offer cannot move the SBM")
    elif margin < policy.min_gross_margin:
        rework.append(f"gross margin {margin:.0%} < floor {policy.min_gross_margin:.0%}")

    max_loss = _num(opp, "finance", "max_loss_usd", default=float("inf"))
    if max_loss > policy.loss_cap_usd:
        rework.append(f"worst-case loss ${max_loss:,.0f} exceeds cap ${policy.loss_cap_usd:,.0f}")

    delivery = _num(opp, "offer", "delivery_days", default=float("inf"))
    if delivery > policy.timebox_days:
        rework.append(f"first delivery {delivery:g}d exceeds {policy.timebox_days}d time box")

    for flag in opp.get("legal", {}).get("flags", []):
        if flag.get("blocking"):
            hold.append(f"legal: {flag.get('issue')}")

    queue = []
    for action in opp.get("actions", []):
        kind = action.get("type")
        if kind in CONSEQUENTIAL_ACTIONS:
            queue.append({"opportunity": name, "type": kind,
                          "description": action.get("description", ""),
                          "requires_human_approval": True})
        if kind == "raise_capital" and action.get("passive_investors", True):
            hold.append("passive capital: securities counsel and an exemption required")

    if kill:
        decision, reasons = KILL, kill
    elif hold:
        decision, reasons = HOLD, hold + rework
    elif rework:
        decision, reasons = REWORK, rework
    else:
        decision, reasons = GO, ["all gates passed; awaiting Alfonso's decision"]

    expected_paid = _num(opp, "finance", "expected_paid_commitments_14d")
    projected_net = round((price - unit_cost) * expected_paid, 2)
    leverage = projected_net / max(max_loss, 1.0) if max_loss != float("inf") else 0.0
    if opp.get("network_edge"):
        leverage *= 1.5                    # trusted access is the wedge the plan rests on

    return {"name": name, "decision": decision, "decision_verb": DECISION_VERB[decision],
            "reasons": reasons,
            "gross_margin": round(margin, 3), "projected_net_30d_usd": projected_net,
            "max_loss_usd": max_loss if max_loss != float("inf") else None,
            "network_edge": bool(opp.get("network_edge")),
            "leverage": round(leverage, 3),
            "human_queue": queue if decision in (GO, HOLD) else []}


def govern(dossier: dict) -> dict:
    """Decide every opportunity in an agent-produced dossier."""
    if not isinstance(dossier, dict) or not isinstance(dossier.get("opportunities"), list):
        raise GovernorRefusal("dossier requires an 'opportunities' list")
    policy = Policy(**dossier.get("policy", {}))
    problems = policy.validate()
    if problems:
        raise GovernorRefusal(f"invalid policy: {problems}")

    results = [assess(o, policy) for o in dossier["opportunities"]]
    ranked = sorted((r for r in results if r["decision"] == GO),
                    key=lambda r: r["leverage"], reverse=True)
    return {
        "sbm": SBM,
        "policy": policy.__dict__,
        "ranked_go": [r["name"] for r in ranked],
        "decisions": results,
        "human_decision_queue": [q for r in results for q in r["human_queue"]],
        "counts": {d: sum(r["decision"] == d for r in results)
                   for d in (GO, REWORK, KILL, HOLD)},
        "requires_human_approval": True,   # hardcoded
        "execution_authority": False,      # hardcoded: the governor never launches
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m src.services.uat_governor <dossier.json>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        dossier = json.load(fh)
    try:
        print(json.dumps(govern(dossier), indent=2))
    except GovernorRefusal as exc:
        print(json.dumps({"refused": str(exc), "execution_authority": False}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
