"""Phase 7 — the Regenerative Treasury waterfall.

Doctrine (CAPITAL): revenue flows through one waterfall, in priority
order, and every allocation is a policy decision — never an autonomous
fund movement:

    1. operating costs   (the machine keeps itself alive)
    2. reserve floor     (survival buffer; an absolute floor, not a share)
    3. regenerative share (a FLOOR, not a ceiling — regeneration is not
                          optional; default minimum 10%)
    4. founder distribution (last, and only what remains)

Hard invariants:
  - negative revenue refuses (the waterfall never allocates a hole)
  - shares sum to at most 1.0; the rounding remainder goes to reserve,
    never to the founder
  - the reserve floor is funded before any distribution
  - every plan requires human ratification: requires_human_approval is
    hardcoded True and execution_authority is hardcoded False
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

MIN_REGENERATIVE_SHARE = 0.10            # regeneration is not optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TreasuryRefusal(ValueError):
    """Invalid policy or inadmissible revenue. Fails closed."""


@dataclass
class WaterfallPolicy:
    operating_share: float               # fraction of revenue for operating costs
    reserve_floor_usd: float             # absolute floor funded before any distribution
    regenerative_share: float            # >= MIN_REGENERATIVE_SHARE
    founder_share: float                 # what remains for the operator

    def validate(self) -> list[str]:
        problems = []
        for name in ("operating_share", "regenerative_share", "founder_share"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                problems.append(f"{name} out of [0,1]: {v}")
        if self.reserve_floor_usd < 0:
            problems.append("reserve floor may not be negative")
        if self.regenerative_share < MIN_REGENERATIVE_SHARE:
            problems.append(f"regenerative share {self.regenerative_share} below the "
                            f"{MIN_REGENERATIVE_SHARE} floor; regeneration is not optional")
        if self.operating_share + self.regenerative_share + self.founder_share > 1.0 + 1e-9:
            problems.append("shares exceed 1.0; the waterfall cannot promise more than revenue")
        return problems


@dataclass
class AllocationPlan:
    revenue_usd: float
    operating_usd: float
    reserve_usd: float
    regenerative_usd: float
    founder_usd: float
    fully_allocated: bool
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)
    requires_human_approval: bool = True     # hardcoded
    execution_authority: bool = False        # hardcoded: plans never move funds

    def to_dict(self) -> dict:
        return {"plan_id": self.plan_id, "revenue_usd": self.revenue_usd,
                "operating_usd": self.operating_usd, "reserve_usd": self.reserve_usd,
                "regenerative_usd": self.regenerative_usd, "founder_usd": self.founder_usd,
                "fully_allocated": self.fully_allocated,
                "requires_human_approval": self.requires_human_approval,
                "execution_authority": self.execution_authority,
                "created_at": self.created_at}


class RegenerativeTreasury:
    """Computes allocation plans. Movement is the human's, after ratification."""

    def waterfall(self, revenue_usd: float, policy: WaterfallPolicy) -> AllocationPlan:
        if revenue_usd < 0:
            raise TreasuryRefusal("negative revenue is inadmissible; the waterfall "
                                  "never allocates a hole")
        problems = policy.validate()
        if problems:
            raise TreasuryRefusal(f"invalid waterfall policy: {problems}")

        operating = round(revenue_usd * policy.operating_share, 2)
        after_operating = revenue_usd - operating

        # reserve floor is absolute and funded before any distribution
        reserve = min(max(policy.reserve_floor_usd, 0.0), after_operating)
        distributable = after_operating - reserve

        regenerative = round(distributable * policy.regenerative_share, 2)
        founder = round(distributable * policy.founder_share, 2)

        # the rounding remainder goes to reserve, never to the founder
        remainder = round(distributable - regenerative - founder, 2)
        if remainder > 0:
            reserve = round(reserve + remainder, 2)
        elif remainder < 0:                # over-allocation: founder absorbs the shortfall
            founder = round(founder + remainder, 2)
            if founder < 0:
                raise TreasuryRefusal("allocation arithmetic fault; refusing the plan")

        total = round(operating + reserve + regenerative + founder, 2)
        return AllocationPlan(
            revenue_usd=revenue_usd, operating_usd=operating, reserve_usd=reserve,
            regenerative_usd=regenerative, founder_usd=founder,
            fully_allocated=abs(total - revenue_usd) < 0.005)
