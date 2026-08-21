"""Phase 7 tests: the Regenerative Treasury waterfall.

Priority order is law: operating, reserve floor, regenerative share
(a floor, never below 10%), founder last. Negative revenue refuses.
Remainders go to reserve, never the founder. Plans never move funds.
"""
import pytest

from src.services.treasury import (MIN_REGENERATIVE_SHARE, RegenerativeTreasury,
                                   TreasuryRefusal, WaterfallPolicy)


def _policy(**kw):
    base = dict(operating_share=0.40, reserve_floor_usd=500.0,
                regenerative_share=0.20, founder_share=0.40)
    base.update(kw)
    return WaterfallPolicy(**base)


class TestPolicyContract:
    def test_regenerative_floor_enforced(self):
        t = RegenerativeTreasury()
        with pytest.raises(TreasuryRefusal, match="regeneration is not optional"):
            t.waterfall(1000.0, _policy(regenerative_share=MIN_REGENERATIVE_SHARE - 0.01))

    def test_shares_above_one_refused(self):
        t = RegenerativeTreasury()
        with pytest.raises(TreasuryRefusal, match="exceed 1.0"):
            t.waterfall(1000.0, _policy(operating_share=0.6, founder_share=0.6))

    def test_negative_revenue_refused(self):
        with pytest.raises(TreasuryRefusal, match="negative revenue"):
            RegenerativeTreasury().waterfall(-1.0, _policy())


class TestWaterfall:
    def test_priority_order_and_full_allocation(self):
        plan = RegenerativeTreasury().waterfall(10_000.0, _policy())
        assert plan.operating_usd == 4000.0
        assert plan.reserve_usd >= 500.0                # floor funded before distribution
        assert plan.regenerative_usd == pytest.approx(
            (10_000 - 4000 - 500) * 0.20, abs=0.02)
        total = plan.operating_usd + plan.reserve_usd + plan.regenerative_usd + plan.founder_usd
        assert total == pytest.approx(10_000.0, abs=0.01)
        assert plan.fully_allocated

    def test_rounding_remainder_goes_to_reserve_never_founder(self):
        plan = RegenerativeTreasury().waterfall(0.03, _policy(reserve_floor_usd=0.0))
        total = plan.operating_usd + plan.reserve_usd + plan.regenerative_usd + plan.founder_usd
        assert total <= 0.031                            # never invents money
        assert plan.founder_usd <= 0.03 * 0.40 + 0.005   # founder never pockets rounding

    def test_tiny_revenue_funds_reserve_first(self):
        plan = RegenerativeTreasury().waterfall(100.0, _policy())
        # operating 40, then reserve floor takes up to 60 remaining entirely
        assert plan.reserve_usd == 60.0
        assert plan.regenerative_usd == 0.0 and plan.founder_usd == 0.0

    def test_plans_never_execute(self):
        plan = RegenerativeTreasury().waterfall(5_000.0, _policy())
        assert plan.requires_human_approval is True
        assert plan.execution_authority is False
