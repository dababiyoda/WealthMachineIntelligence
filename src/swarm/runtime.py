"""UAT swarm runtime: the Income Streams Loop, run by real agents, on the record.

One cycle:

    scout (Prometheus) -> per opportunity, as a mission in the ledger:
      diligence (Logos) -> red team (Veritas / Aegis / Strategos, routed to a
      different model lineage than the producer where one exists) -> offer
      (Daedalus) -> finance (Aurelius) + legal (Aegis) -> drafts (Concord)
      -> deterministic governor -> independent review -> decision verb
    -> every stage recorded as a graded outcome; a founder brief written.

Production guards:
  * kill switch   UAT_SWARM_PAUSED=1 refuses to start a cycle
  * budget        a per-cycle USD ceiling; the next call is refused once spent
  * isolation     a stage failure (refusal, truncation, bad JSON) blocks that
                  mission only; the cycle continues
  * idempotency   missions already in the ledger are skipped; the scout
                  result is cached per run, so a rerun resumes instead of
                  repaying
  * authority     no stage can send, spend, sign or publish; every
                  consequential step lands in the human decision queue
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.services.uat_governor import govern
from src.services.uat_missions import TRANSITIONS
from src.services.uat_store import UATStore

from .model import ModelClient, ModelError
from .roles import RED_STAGES, STAGES, system_prompt

GO = "GO"


class SwarmPaused(RuntimeError):
    """The kill switch is set."""


class BudgetExceeded(RuntimeError):
    """The cycle's spending ceiling is reached."""


@dataclass
class RuntimeConfig:
    cash_cap_usd: float = 0.0            # Alfonso's standing grant: $0 new spending
    timebox_days: int = 30
    min_gross_margin: float = 0.6
    max_opportunities: int = 4
    cycle_budget_usd: float = 25.0       # model + search spend per cycle
    out_dir: str = "runs/uat"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:60] or "unnamed"


class SwarmRuntime:
    def __init__(self, store: UATStore, clients: list[ModelClient],
                 config: RuntimeConfig | None = None) -> None:
        if not clients:
            raise ValueError("at least one model client is required")
        self.store = store
        self.clients = {c.lineage: c for c in clients}
        self.config = config or RuntimeConfig()
        self.spent_usd = 0.0
        self._ensure_agents()

    # -- setup ----------------------------------------------------------------
    def _ensure_agents(self) -> None:
        slots = {spec[0] for spec in STAGES.values()}
        for slot in sorted(slots):
            for lineage in self.clients:
                agent_id = f"{slot.lower()}-{lineage}"
                if agent_id not in self.store.swarm.agents:
                    self.store.execute("register_agent", {"agent_id": agent_id, "slot": slot,
                                                          "lineage": lineage, "principal": "UAT"})

    # -- one agent call --------------------------------------------------------
    def _call(self, stage: str, key: str, task: str, now: datetime,
              avoid_lineage: str | None = None) -> tuple[str, dict, float]:
        if self.spent_usd >= self.config.cycle_budget_usd:
            raise BudgetExceeded(f"cycle budget ${self.config.cycle_budget_usd:.2f} reached")
        slot, _, _, schema, web = STAGES[stage]
        agent_id = self.store.swarm.route(f"{key}:{stage}", stage, slot, now)["agent_id"]
        lineage = self.store.swarm.agents[agent_id].lineage
        if avoid_lineage and lineage == avoid_lineage:
            others = [lin for lin in self.clients if lin != avoid_lineage]
            if others:                                   # cross-lineage review when possible
                lineage, agent_id = others[0], f"{slot.lower()}-{others[0]}"
        completion = self.clients[lineage].complete(system_prompt(stage), task, schema, web)
        self.spent_usd += completion.cost_usd
        return agent_id, completion.data, completion.cost_usd

    # -- the cycle ---------------------------------------------------------------
    def run_cycle(self, run_id: str, focus: str, now: datetime | None = None) -> dict:
        if os.getenv("UAT_SWARM_PAUSED", "").strip() not in ("", "0", "false"):
            raise SwarmPaused("UAT_SWARM_PAUSED is set; no cycle started")
        now = now or datetime.now(timezone.utc)
        os.makedirs(self.config.out_dir, exist_ok=True)

        opportunities, scout_agent, scout_cost = self._scout(run_id, focus, now)
        results, blocked, stopped = [], [], None
        for opp in opportunities[: self.config.max_opportunities]:
            mission_id = f"{run_id}:{_slug(opp['name'])}"
            if mission_id in self.store.record.missions:
                continue                                 # resume: already decided or blocked
            try:
                results.append(self._mission(mission_id, opp, focus, now))
            except BudgetExceeded as exc:
                stopped = str(exc)
                self._block(mission_id, stopped)
                break
            except ModelError as exc:
                blocked.append({"mission_id": mission_id, "reason": str(exc)})
                self._block(mission_id, str(exc))

        any_go = any(r["decision"] == GO for r in results)
        if scout_agent:
            self._outcome(scout_agent, f"{run_id}:scout", "scout", any_go, scout_cost, now)
        brief = self._write_brief(run_id, focus, results, blocked, stopped)
        return {"run_id": run_id, "missions": [r["mission_id"] for r in results],
                "ranked_go": [r["mission_id"] for r in
                              sorted((r for r in results if r["decision"] == GO),
                                     key=lambda r: r["leverage"], reverse=True)],
                "blocked": blocked, "stopped": stopped, "spent_usd": round(self.spent_usd, 4),
                "brief_path": brief, "execution_authority": False}

    def _scout(self, run_id: str, focus: str, now: datetime):
        cache = os.path.join(self.config.out_dir, f"{_slug(run_id)}-scout.json")
        if os.path.exists(cache):
            with open(cache, encoding="utf-8") as fh:
                return json.load(fh)["opportunities"], None, 0.0
        task = (f"FOCUS: {focus}\nCash cap: ${self.config.cash_cap_usd:.0f}. "
                f"Time box to first paid delivery: {self.config.timebox_days} days.")
        agent, data, cost = self._call("scout", run_id, task, now)
        with open(cache, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return data["opportunities"], agent, cost

    def _mission(self, mission_id: str, opp: dict, focus: str, now: datetime) -> dict:
        ex = self.store.execute
        ex("open_mission", {
            "mission_id": mission_id, "venture_id": _slug(opp["name"]), "owner": "Logos",
            "reviewer": "Veritas", "bounded_outcome": f"decision-ready dossier: {opp['name']}",
            "active_bottleneck": "first paid commitment",
            "acceptance_criteria": "governor gates pass with >=2 independent sources",
            "deadline": (now + timedelta(days=self.config.timebox_days)).isoformat(),
            "origin_group": "Opportunity Foundry"})
        for state in ("SCOPED", "AUTHORIZED", "READY", "RUNNING"):
            ex("transition", {"mission_id": mission_id, "state": state, "by": "Logos"})
        ex("claim", {"mission_id": mission_id, "bot": "Logos", "artifact_version": 0})

        brief = json.dumps(opp)
        outputs, agents, costs = {}, {}, {}

        def run(stage: str, task: str, avoid: str | None = None):
            agent, data, cost = self._call(stage, mission_id, task, now, avoid)
            outputs[stage], agents[stage], costs[stage] = data, agent, cost
            self._save(mission_id, stage, data)
            return data

        analyst = run("diligence", f"Opportunity: {brief}")
        producer_lineage = self.store.swarm.agents[agents["diligence"]].lineage
        red = []
        for stage, lens in RED_STAGES.items():
            r = run(stage, f"Opportunity: {brief}\nDiligence: {json.dumps(analyst)}", producer_lineage)
            red.append(dict(r, lens=lens))
        refuted = [r for r in red if r["refuted"]]
        dead = (analyst["verdict"] == "not_viable" or len(refuted) >= 2
                or any(r["severity"] == "critical" for r in refuted))
        if not dead:
            ctx = f"Opportunity: {brief}\nDiligence: {json.dumps(analyst)}\nRed team: {json.dumps(red)}"
            offer = run("offer", f"{ctx}\nTime box: {self.config.timebox_days} days.")
            run("finance", f"{ctx}\nOffer: {json.dumps(offer)}\nCash cap: ${self.config.cash_cap_usd:.0f}.")
            run("legal", f"{ctx}\nOffer: {json.dumps(offer)}")
            run("gtm", f"Offer: {json.dumps(offer)}\nBuyer: {opp.get('buyer', '')}")

        if analyst["verdict"] == "not_viable":
            red.append({"lens": "diligence", "refuted": True, "severity": "critical",
                        "argument": analyst["notes"], "evidence": []})
        dossier = {"policy": {"loss_cap_usd": self.config.cash_cap_usd,
                              "timebox_days": self.config.timebox_days,
                              "min_gross_margin": self.config.min_gross_margin},
                   "opportunities": [{
                       "name": mission_id, "network_edge": False,
                       "evidence": opp.get("evidence", []) + analyst.get("demand_evidence", []),
                       "red_team": red, "offer": outputs.get("offer", {}),
                       "finance": outputs.get("finance", {}),
                       "legal": outputs.get("legal", {"flags": []}),
                       "actions": outputs.get("gtm", {}).get("actions", [])}]}
        verdict = govern(dossier)["decisions"][0]
        self._save(mission_id, "governor", verdict)

        ex("transition", {"mission_id": mission_id, "state": "REVIEW", "by": "Logos"})
        urls = [e["url"] for e in dossier["opportunities"][0]["evidence"]]
        ex("review", {"mission_id": mission_id, "reviewer": "Veritas",
                      "claims": [{"claim": f"demand for {opp['name']}", "evidence": urls}],
                      "criteria_met": verdict["decision"] == GO,
                      "repair": "; ".join(verdict["reasons"])})
        ex("decide", {"mission_id": mission_id, "verb": verdict["decision_verb"], "by": "Hegemony",
                      "rationale": "; ".join(verdict["reasons"])})

        for stage, agent in agents.items():
            if stage in RED_STAGES:
                lens_call = outputs[stage]["refuted"]
                accepted = lens_call == (verdict["decision"] == "KILL")
            else:
                accepted = verdict["decision"] == GO
            self._outcome(agent, mission_id, stage, accepted, costs[stage], now)
        return {"mission_id": mission_id, "name": opp["name"], **verdict,
                "offer": outputs.get("offer"), "finance": outputs.get("finance"),
                "gtm": outputs.get("gtm"), "evidence": urls}

    # -- bookkeeping -------------------------------------------------------------
    def _save(self, mission_id: str, stage: str, data: dict) -> None:
        path = os.path.join(self.config.out_dir, _slug(mission_id), f"{stage}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        self.store.execute("save_artifact", {"mission_id": mission_id, "bot": "Logos",
                                             "artifact_ref": path})

    def _outcome(self, agent_id: str, mission_id: str, stage: str, accepted: bool,
                 cost: float, now: datetime) -> None:
        self.store.execute("record_outcome", {
            "agent_id": agent_id, "mission_id": mission_id, "stage": stage,
            "accepted": accepted, "grade": "deterministic", "reviewer_id": "check:governor",
            "at": now.isoformat(), "cost_usd": round(cost, 6)})

    def _block(self, mission_id: str, reason: str) -> None:
        m = self.store.record.missions.get(mission_id)
        if m and "BLOCKED" in TRANSITIONS[m.state]:
            self.store.execute("transition", {"mission_id": mission_id, "state": "BLOCKED",
                                              "by": "Logos"})

    def _write_brief(self, run_id: str, focus: str, results: list, blocked: list,
                     stopped: str | None) -> str:
        go = sorted((r for r in results if r["decision"] == GO), key=lambda r: r["leverage"], reverse=True)
        lines = [f"# UAT cycle {run_id}", "", f"Focus: {focus}",
                 f"Spend this cycle: ${self.spent_usd:.2f} of ${self.config.cycle_budget_usd:.2f}",
                 "Authority: research and drafts only. Nothing was sent, spent, signed or published.", ""]
        lines += ["## VALIDATE (bounded buyer test, awaiting Alfonso)", ""]
        for r in go:
            o = r.get("offer") or {}
            lines += [f"### {r['name']}", f"- Offer: {o.get('title', '')} at ${o.get('price_usd', 0):,.0f}",
                      f"- Deliverable: {o.get('deliverable', '')}",
                      f"- Worst-case loss: ${r['max_loss_usd'] or 0:,.0f}; projected net 30d: ${r['projected_net_30d_usd']:,.0f}",
                      f"- Kill rules: {'; '.join((r.get('finance') or {}).get('kill_rules', []))}",
                      f"- Evidence: {', '.join(r['evidence'][:5])}", ""]
        if not go:
            lines += ["None this cycle.", ""]
        lines += ["## Human decision queue", ""]
        queue = [q for r in results for q in r["human_queue"]]
        lines += [f"- [{q['type']}] {q['opportunity']}: {q['description']}" for q in queue] or ["- (empty)"]
        lines += ["", "## RECONFIGURE / PARK / KILL", ""]
        lines += [f"- {r['decision_verb']} {r['name']}: {'; '.join(r['reasons'])}"
                  for r in results if r["decision"] != GO] or ["- (none)"]
        if blocked or stopped:
            lines += ["", "## Blocked", ""] + [f"- {b['mission_id']}: {b['reason']}" for b in blocked]
            if stopped:
                lines.append(f"- cycle stopped: {stopped}")
        path = os.path.join(self.config.out_dir, f"{_slug(run_id)}-brief.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return path
