"""UAT earned-authority swarm ledger.

The group-chat design fixes thirteen roles to thirteen bots and reviews
them once, after fourteen days. This module turns each role into a *slot*
that any number of agents may fill — Grok bots, Claude agents, or human
network members running their own agents — and lets four mechanisms,
mutated from that design, interact:

    proof grading      acceptance counts only as strongly as its reviewer is
                       independent: same-lineage review earns nothing (LLM
                       judges favor their own family's output), deterministic
                       checks earn some, a different-lineage reviewer more,
                       an external buyer or verifier most. Synthetic work
                       earns nothing.
    earned autonomy    per-stage, decaying reputation sets an agent's tier:
                       how much of its work is sampled for review and how many
                       missions it may run at once. Rejections contract the
                       tier immediately. No tier ever grants an external
                       effect — that stays with Alfonso's grants.
    proof-weighted     each mission goes to the eligible agent with the best
    routing            earned record for that stage, with a deterministic
                       exploration slot so new agents and members can earn.
    contribution       collected cash on a mission is attributed to the human
    settlement         principals behind the agents and reviewers whose
                       accepted work produced it — a plan for ratification,
                       never a payment.

Emergent capability: the swarm can add agents and members without adding
founder attention or review load, because trust, routing and reward all
come from one record of independently accepted, collected outcomes — and
any of them can lose standing the same way.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

GRADE_WEIGHT = {"internal": 0.0, "deterministic": 0.5, "independent": 1.0, "external": 2.0}
REJECTION_PENALTY = 2.0                  # a rejection costs twice what an acceptance earns
HALF_LIFE_DAYS = 30.0                    # standing must keep being re-earned
RECIPROCITY_DISCOUNT = 0.5               # pairs who only vouch for each other count half
EXPLORE_EVERY = 5                        # one mission in five goes to the least-proven agent
REVIEW_CREDIT = 0.25                     # a reviewer's share unit relative to a producer's 1.0
CONTRACTION_WINDOW = timedelta(days=14)

# tier: (min score, min external acceptances, review sample rate, concurrent missions)
TIERS = (
    ("T0-probation", 0.0, 0, 1.00, 1),
    ("T1-trusted", 3.0, 1, 0.50, 2),
    ("T2-proven", 8.0, 3, 0.20, 3),
)


class SwarmRefusal(ValueError):
    """The ledger refuses an inadmissible record. Fails closed."""


@dataclass(frozen=True)
class Agent:
    agent_id: str
    slot: str                            # role it may fill, e.g. "Concord"
    lineage: str                         # "grok", "claude", "human", ... (model family)
    principal: str = "UAT"               # human who receives contribution credit


@dataclass(frozen=True)
class Outcome:
    agent_id: str
    mission_id: str
    stage: str
    accepted: bool
    grade: str
    reviewer_id: str                     # agent id, or "external:<actor>" / "check:<name>"
    at: datetime
    synthetic: bool = False
    cost_usd: float = 0.0
    founder_minutes: float = 0.0


class SwarmLedger:
    """One record of who did what, how well it was proven, and what it earned."""

    execution_authority = False          # hardcoded: the ledger never acts

    def __init__(self) -> None:
        self.agents: dict[str, Agent] = {}
        self.outcomes: list[Outcome] = []

    # -- membership ------------------------------------------------------
    def register(self, agent: Agent) -> Agent:
        if agent.agent_id in self.agents:
            raise SwarmRefusal(f"{agent.agent_id} already registered")
        self.agents[agent.agent_id] = agent
        return agent

    def _agent(self, agent_id: str) -> Agent:
        if agent_id not in self.agents:
            raise SwarmRefusal(f"unknown agent {agent_id}")
        return self.agents[agent_id]

    # -- proof grading -----------------------------------------------------
    def effective_grade(self, outcome: Outcome) -> str:
        """Downgrade any claim of independence the record cannot support."""
        if outcome.synthetic:
            return "internal"
        rid = outcome.reviewer_id
        if rid.startswith("external:"):
            return outcome.grade
        if rid.startswith("check:"):
            return "deterministic" if outcome.grade != "internal" else "internal"
        reviewer = self._agent(rid)
        if reviewer.lineage == self.agents[outcome.agent_id].lineage and outcome.grade != "internal":
            return "internal"            # same model family: self-preference risk
        if outcome.grade == "external":
            return "independent"         # only an outside actor can confer external
        return outcome.grade

    def record(self, outcome: Outcome) -> Outcome:
        agent = self._agent(outcome.agent_id)
        if outcome.grade not in GRADE_WEIGHT:
            raise SwarmRefusal(f"unknown grade {outcome.grade!r}")
        if outcome.reviewer_id == agent.agent_id:
            raise SwarmRefusal("an agent cannot review its own work")
        if not outcome.reviewer_id.startswith(("external:", "check:")):
            reviewer = self._agent(outcome.reviewer_id)
            if reviewer.principal == agent.principal and agent.principal != "UAT":
                raise SwarmRefusal("a member's agents cannot review each other for credit")
        self.outcomes.append(outcome)
        return outcome

    # -- earned standing -----------------------------------------------------
    def _reciprocal(self, a: str, b: str) -> bool:
        ab = any(o.agent_id == a and o.reviewer_id == b for o in self.outcomes)
        ba = any(o.agent_id == b and o.reviewer_id == a for o in self.outcomes)
        return ab and ba

    def standing(self, agent_id: str, stage: str, now: datetime) -> dict:
        self._agent(agent_id)
        score, evidence, external, rejected_recently = 0.0, 0, 0, False
        for o in self.outcomes:
            if o.agent_id != agent_id or o.stage != stage:
                continue
            weight = GRADE_WEIGHT[self.effective_grade(o)]
            if weight == 0:
                continue
            age_days = max((now - o.at).total_seconds() / 86400, 0.0)
            weight *= 0.5 ** (age_days / HALF_LIFE_DAYS)
            if not o.reviewer_id.startswith(("external:", "check:")) and \
                    self._reciprocal(agent_id, o.reviewer_id):
                weight *= RECIPROCITY_DISCOUNT
            evidence += 1
            if o.accepted:
                score += weight
                external += self.effective_grade(o) == "external"
            else:
                score -= REJECTION_PENALTY * weight
                rejected_recently |= now - o.at <= CONTRACTION_WINDOW
        return {"score": round(score, 3), "evidence": evidence, "external": external,
                "rejected_recently": rejected_recently}

    def tier(self, agent_id: str, stage: str, now: datetime) -> dict:
        s = self.standing(agent_id, stage, now)
        level = 0
        for i, (_, min_score, min_ext, _, _) in enumerate(TIERS):
            if s["score"] >= min_score and s["external"] >= min_ext:
                level = i
        if s["rejected_recently"]:
            level = max(level - 1, 0)    # contraction is immediate; expansion is earned
        name, _, _, sample, concurrency = TIERS[level]
        return {"tier": name, "review_sample_rate": sample, "max_concurrent": concurrency,
                "grants_external_authority": False, **s}

    # -- routing ------------------------------------------------------------
    def route(self, mission_id: str, stage: str, slot: str, now: datetime,
              active: dict[str, int] | None = None) -> dict:
        active = active or {}
        pool = []
        for a in self.agents.values():
            if a.slot != slot:
                continue
            t = self.tier(a.agent_id, stage, now)
            if active.get(a.agent_id, 0) < t["max_concurrent"]:
                pool.append((a.agent_id, t))
        if not pool:
            raise SwarmRefusal(f"no eligible agent with capacity for {slot}/{stage}")
        bucket = int(hashlib.sha256(mission_id.encode()).hexdigest(), 16) % EXPLORE_EVERY
        if bucket == 0 and len(pool) > 1:
            agent_id, t = min(pool, key=lambda p: (p[1]["evidence"], p[0]))
            reason = "exploration: least-proven eligible agent"
        else:
            agent_id, t = max(pool, key=lambda p: (p[1]["score"], -p[1]["evidence"], p[0]))
            reason = "exploitation: best earned standing"
        return {"mission_id": mission_id, "agent_id": agent_id, "reason": reason,
                "review_sample_rate": t["review_sample_rate"], "tier": t["tier"],
                "execution_authority": False}

    # -- settlement ---------------------------------------------------------
    def contribution_plan(self, mission_id: str, distributable_usd: float) -> dict:
        """Split a mission's distributable cash by accepted, graded work.

        distributable_usd is what remains after the treasury waterfall
        (operating, reserve floor, regenerative share). The output is a plan
        that requires human ratification; it never moves money.
        """
        if distributable_usd < 0:
            raise SwarmRefusal("cannot distribute a negative amount")
        units: dict[str, float] = defaultdict(float)
        for o in self.outcomes:
            if o.mission_id != mission_id or not o.accepted:
                continue
            if GRADE_WEIGHT[self.effective_grade(o)] == 0:
                continue                 # unproven or synthetic work earns no share
            units[self.agents[o.agent_id].principal] += 1.0
            if o.reviewer_id in self.agents:
                units[self.agents[o.reviewer_id].principal] += REVIEW_CREDIT
        total = sum(units.values())
        shares = {p: round(distributable_usd * u / total, 2) for p, u in units.items()} if total else {}
        remainder = round(distributable_usd - sum(shares.values()), 2)
        if remainder:
            shares["UAT"] = round(shares.get("UAT", 0.0) + remainder, 2)  # rounding stays in-house
        return {"mission_id": mission_id, "shares": shares, "units": dict(units),
                "requires_human_approval": True, "execution_authority": False}

    # -- continuous selection ------------------------------------------------
    def slot_review(self, now: datetime, window: timedelta = CONTRACTION_WINDOW) -> dict:
        """The design's 14-day review, run continuously per slot."""
        report = {}
        for slot in sorted({a.slot for a in self.agents.values()}):
            ids = {a.agent_id for a in self.agents.values() if a.slot == slot}
            recent = [o for o in self.outcomes if o.agent_id in ids and now - o.at <= window]
            proven = [o for o in recent if o.accepted and GRADE_WEIGHT[self.effective_grade(o)] > 0]
            cost = sum(o.cost_usd for o in recent)
            minutes = sum(o.founder_minutes for o in recent)
            if proven:
                verdict = "KEEP"
            elif recent:
                verdict = "MERGE-OR-PAUSE"   # active but nothing independently accepted
            else:
                verdict = "DORMANT"          # dormant roles are not failed roles
            report[slot] = {"agents": len(ids), "proven": len(proven), "cost_usd": cost,
                            "founder_minutes": minutes, "verdict": verdict}
        return report


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)
