"""Phase 7 — the first digital business loop.

One complete, bounded loop from signal to settlement:

    opportunity (kernel-format packet) -> validation gate -> offer
    construction -> human gate -> simulated settlement -> treasury
    waterfall -> reconciliation -> learning record

Every stage is recorded. The human gate is structural: no offer leaves
without ratification, and settlement is SIMULATED (a rehearsal of the
money path, not a movement of money) until the operator wires real rails
through the kernel Consequence Gate.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .treasury import RegenerativeTreasury, WaterfallPolicy


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class LoopRefusal(ValueError):
    """The loop cannot proceed; it fails closed with named reasons."""


@dataclass
class Offer:
    title: str
    price_usd: float
    delivery: str                          # what the buyer receives
    reversible: bool = True                # irreversible offers refuse

    def validate(self) -> list[str]:
        problems = []
        if not self.title or not self.delivery:
            problems.append("offer requires title and delivery")
        if self.price_usd < 0:
            problems.append("price may not be negative")
        if not self.reversible:
            problems.append("irreversible offers refuse: the first loop is always refundable")
        return problems


@dataclass
class LoopRecord:
    loop_id: str
    packet_id: str
    stage: str                             # current/final stage
    history: list[dict] = field(default_factory=list)
    verdict: str | None = None             # "settled" | "refused:<reason>"
    revenue_usd: float = 0.0
    allocation: dict | None = None

    def log(self, stage: str, **data) -> None:
        self.stage = stage
        self.history.append({"stage": stage, "at": _now(), **data})


class DigitalBusinessLoop:
    """The smallest honest business: validate, offer, settle (simulated),
    allocate, reconcile, learn."""

    def __init__(self, *, validator, treasury_policy: WaterfallPolicy,
                 ledger=None, legal_operator: str = "alfonso_lopez"):
        """validator: callable(packet) -> verdict string in
        {"go", "defer", "kill", "needs_more_evidence"} (the venture engine)."""
        if legal_operator == "UNIIMENTE":
            raise LoopRefusal("UNIIMENTE is never a legal operator")
        problems = treasury_policy.validate()
        if problems:
            raise LoopRefusal(f"invalid treasury policy: {problems}")
        self.validator = validator
        self.treasury = RegenerativeTreasury()
        self.policy = treasury_policy
        self.ledger = ledger
        self.legal_operator = legal_operator

    def _record(self, rec: LoopRecord) -> None:
        if self.ledger is not None:
            self.ledger.append("event", {"type": "business.loop",
                                         "loop_id": rec.loop_id, **rec.__dict__})

    def run(self, packet: dict, offer: Offer, *, ratifier=None) -> LoopRecord:
        rec = LoopRecord(loop_id=str(uuid.uuid4()),
                         packet_id=str(packet.get("packet_id", "unknown")),
                         stage="intake")

        # 1. validation gate: the venture engine judges; only "go" proceeds
        verdict = self.validator(packet)
        rec.log("validated", verdict=verdict)
        if verdict != "go":
            rec.verdict = f"refused:validator_{verdict}"
            self._record(rec)
            return rec

        # 2. offer construction: bounded, reversible, honest
        problems = offer.validate()
        if problems:
            rec.verdict = f"refused:offer_invalid"
            rec.log("offer_refused", problems=problems)
            self._record(rec)
            return rec
        rec.log("offer_constructed", title=offer.title, price_usd=offer.price_usd)

        # 3. the human gate: no ratifier, no offer leaves
        approved = bool(ratifier and ratifier(offer))
        rec.log("human_gate", approved=approved)
        if not approved:
            rec.verdict = "refused:human_gate"
            self._record(rec)
            return rec

        # 4. simulated settlement: a rehearsal of the money path
        rec.revenue_usd = offer.price_usd
        rec.log("settled_simulated", revenue_usd=rec.revenue_usd)

        # 5. treasury waterfall: allocation plan (never movement)
        plan = self.treasury.waterfall(rec.revenue_usd, self.policy)
        rec.allocation = plan.to_dict()
        rec.log("allocated", plan_id=plan.plan_id)

        # 6. reconciliation + learning: the loop closes with a record
        rec.verdict = "settled"
        rec.log("reconciled", learning=f"offer {offer.title!r} settled at "
                                       f"${rec.revenue_usd:.2f} under policy")
        self._record(rec)
        return rec
