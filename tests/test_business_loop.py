"""Phase 7 tests: the first digital business loop.

The loop validates, constructs, gates on the human, settles (simulated),
allocates through the treasury, reconciles, and learns. Every refusal
path is a record, not an exception into the void.
"""
import pytest

from src.services.business_loop import DigitalBusinessLoop, LoopRefusal, Offer


def _loop(verdict="go", **kw):
    policy = kw.pop("policy", None) or __import__("src.services.treasury", fromlist=["WaterfallPolicy"]).WaterfallPolicy(
        operating_share=0.4, reserve_floor_usd=50.0, regenerative_share=0.2,
        founder_share=0.4)
    return DigitalBusinessLoop(validator=lambda packet: verdict,
                               treasury_policy=policy, **kw)


def _offer(**kw):
    base = dict(title="Governance checklist", price_usd=49.0,
                delivery="immediate digital download")
    base.update(kw)
    return Offer(**base)


class TestLoopContract:
    def test_only_go_proceeds(self):
        for verdict in ("defer", "kill", "needs_more_evidence"):
            rec = _loop(verdict=verdict).run({"packet_id": "p1"}, _offer(),
                                             ratifier=lambda o: True)
            assert rec.verdict == f"refused:validator_{verdict}"
            assert rec.revenue_usd == 0.0

    def test_irreversible_offer_refused(self):
        rec = _loop().run({"packet_id": "p1"}, _offer(reversible=False),
                          ratifier=lambda o: True)
        assert rec.verdict == "refused:offer_invalid"

    def test_human_gate_blocks_unratified_offers(self):
        rec = _loop().run({"packet_id": "p1"}, _offer(), ratifier=None)
        assert rec.verdict == "refused:human_gate" and rec.revenue_usd == 0.0
        rec2 = _loop().run({"packet_id": "p1"}, _offer(), ratifier=lambda o: False)
        assert rec2.verdict == "refused:human_gate"

    def test_full_loop_settles_and_allocates(self):
        rec = _loop().run({"packet_id": "p1"}, _offer(), ratifier=lambda o: True)
        assert rec.verdict == "settled"
        assert rec.revenue_usd == 49.0
        alloc = rec.allocation
        assert alloc["requires_human_approval"] is True
        assert alloc["execution_authority"] is False
        assert alloc["regenerative_usd"] >= 0.0
        stages = [h["stage"] for h in rec.history]
        assert stages == ["validated", "offer_constructed", "human_gate",
                          "settled_simulated", "allocated", "reconciled"]

    def test_uniimente_never_operator(self):
        with pytest.raises(LoopRefusal, match="UNIIMENTE"):
            _loop(legal_operator="UNIIMENTE")

    def test_invalid_policy_refused_at_construction(self):
        from src.services.treasury import WaterfallPolicy
        bad = WaterfallPolicy(operating_share=0.4, reserve_floor_usd=0.0,
                              regenerative_share=0.0, founder_share=0.6)
        with pytest.raises(LoopRefusal, match="treasury policy"):
            _loop(policy=bad)
