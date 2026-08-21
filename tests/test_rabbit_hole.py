"""Phase 6 tests: the Rabbit Hole Engine's ethics law.

Depth is earned, bounded, and honest. Every recommendation carries an
exit ramp. Dark patterns never enter the graph. After the session
ceiling, the only recommendation is to stop.
"""
import pytest

from src.services.rabbit_hole import (AudienceState, ContentNode, MAX_SESSION_DEPTH,
                                      RabbitHoleEngine, RabbitHoleRefusal)


def _engine():
    e = RabbitHoleEngine()
    e.add_node(ContentNode(node_id="n0", title="What is a gate", depth=0,
                           declares="explainer", value_offered="concept clarity"))
    e.add_node(ContentNode(node_id="n1", title="How gates fail", depth=1,
                           declares="case study", value_offered="failure literacy",
                           next_nodes=["n2"]))
    e.add_node(ContentNode(node_id="n2", title="Build your own gate", depth=2,
                           declares="workshop", value_offered="a working gate"))
    e.nodes["n0"].next_nodes.append("n1")
    return e


class TestNodeContract:
    def test_undeclared_node_refused(self):
        e = RabbitHoleEngine()
        with pytest.raises(RabbitHoleRefusal, match="declare"):
            e.add_node(ContentNode(node_id="x", title="t", depth=0, declares="",
                                   value_offered="v"))

    def test_dark_pattern_node_refused(self):
        e = RabbitHoleEngine()
        with pytest.raises(RabbitHoleRefusal, match="prohibited pattern"):
            e.add_node(ContentNode(node_id="x", title="Act now — secret method", depth=0,
                                   declares="ad", value_offered="v"))


class TestProgression:
    def test_entry_recommends_surface(self):
        e = _engine()
        rec = e.recommend(AudienceState(session_id="s1"))
        assert rec.node_id == "n0" and rec.exit_ramp

    def test_progression_is_earned_by_consumption(self):
        e = _engine()
        state = AudienceState(session_id="s2")
        e.consume(state, "n0")
        rec = e.recommend(state)
        assert rec.node_id == "n1" and rec.depth_after == 2  # consumed: n0 + n1
        # cannot skip: n2 only reachable through n1's frontier
        e.consume(state, "n1")
        assert e.recommend(state).node_id == "n2"

    def test_every_recommendation_carries_exit_ramp(self):
        e = _engine()
        state = AudienceState(session_id="s3")
        for _ in range(3):
            rec = e.recommend(state)
            assert rec.exit_ramp
            if rec.node_id is None:
                break
            e.consume(state, rec.node_id)

    def test_frontier_exhaustion_recommends_exit(self):
        e = _engine()
        state = AudienceState(session_id="s4")
        for nid in ("n0", "n1", "n2"):
            e.consume(state, nid)
        rec = e.recommend(state)
        assert rec.node_id is None and "complete" in rec.exit_ramp

    def test_session_ceiling_forces_exit(self):
        e = _engine()
        state = AudienceState(session_id="s5",
                              consumed=["n0", "n1", "n2", "n0", "n1"])  # depth 5
        rec = e.recommend(state)
        assert rec.node_id is None
        assert "ceiling" in rec.reason
        assert state.depth == MAX_SESSION_DEPTH
