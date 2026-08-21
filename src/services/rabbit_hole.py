"""Phase 6 — the Rabbit Hole Engine.

A rabbit hole is a content sequence that rewards curiosity with depth:
each step delivers real value and names the next, deeper step. The
engine's job is progression; its law is ethics:

  - every node declares what it is (no disguised ads, no fake stories)
  - prohibited dark patterns refuse the node (artificial scarcity, false
    urgency, hidden costs, guaranteed income, engagement bait lies)
  - depth is bounded per session; after the ceiling, the only honest
    recommendation is the exit ramp
  - every recommendation carries an exit ramp — leaving is always one
    step and never punished
  - progression is earned: a node is recommended only if its predecessors
    were actually consumed

The engine never optimizes for time-on-site. It optimizes for
value-delivered per step, with depth as the proof of value.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PROHIBITED_PATTERNS = (
    "artificial scarcity", "false urgency", "hidden cost", "guaranteed income",
    "risk-free", "act now", "secret they don't want", "engagement bait",
)
MAX_SESSION_DEPTH = 5                    # beyond this, the only next step is the exit


class RabbitHoleRefusal(ValueError):
    """A node or recommendation violates the ethics law. Fails closed."""


@dataclass
class ContentNode:
    node_id: str
    title: str
    depth: int                             # 0 = surface, deeper = more commitment/value
    declares: str                          # what this content honestly is
    value_offered: str                     # the real value delivered at this step
    next_nodes: list[str] = field(default_factory=list)
    body: str = ""

    def validate(self) -> list[str]:
        problems = []
        if not self.declares:
            problems.append("every node must declare what it is")
        if not self.value_offered:
            problems.append("every node must offer real value")
        lowered = f"{self.title} {self.body}".lower()
        for pattern in PROHIBITED_PATTERNS:
            if pattern in lowered:
                problems.append(f"prohibited pattern: {pattern!r}")
        if self.depth < 0:
            problems.append("depth may not be negative")
        return problems


@dataclass
class AudienceState:
    session_id: str
    consumed: list[str] = field(default_factory=list)   # node_ids actually consumed, in order

    @property
    def depth(self) -> int:
        return len(self.consumed)


@dataclass
class Recommendation:
    node_id: str | None                    # None = exit ramp
    reason: str
    exit_ramp: str                         # always present: how to leave, honestly
    depth_after: int


class RabbitHoleEngine:
    def __init__(self):
        self.nodes: dict[str, ContentNode] = {}

    def add_node(self, node: ContentNode) -> ContentNode:
        problems = node.validate()
        if problems:
            raise RabbitHoleRefusal(f"node refused: {problems}")
        self.nodes[node.node_id] = node
        return node

    def recommend(self, state: AudienceState) -> Recommendation:
        """The next honest step. Bounds are structural, not tuned."""
        if state.depth >= MAX_SESSION_DEPTH:
            return Recommendation(
                node_id=None,
                reason=f"session depth ceiling ({MAX_SESSION_DEPTH}) reached; "
                       "the honest recommendation is to stop",
                exit_ramp="end the session here — everything so far stands on its own",
                depth_after=state.depth)
        if not state.consumed:
            surface = [n for n in self.nodes.values() if n.depth == 0]
            if not surface:
                raise RabbitHoleRefusal("no surface content registered")
            node = sorted(surface, key=lambda n: n.node_id)[0]
            return self._rec(node, state, "entry: surface content for a new session")
        current = self.nodes[state.consumed[-1]]
        candidates = [self.nodes[nid] for nid in current.next_nodes if nid in self.nodes]
        # progression is earned: only deeper nodes, only from the consumed frontier
        deeper = [n for n in candidates if n.depth > current.depth
                  and n.node_id not in state.consumed]
        if not deeper:
            return Recommendation(
                node_id=None,
                reason="frontier exhausted; no honest deeper step exists",
                exit_ramp="leave with what you have — the sequence is complete",
                depth_after=state.depth)
        node = sorted(deeper, key=lambda n: (n.depth, n.node_id))[0]
        return self._rec(node, state,
                         f"earned progression from depth {current.depth} to {node.depth}")

    def _rec(self, node: ContentNode, state: AudienceState, reason: str) -> Recommendation:
        return Recommendation(
            node_id=node.node_id,
            reason=reason,
            exit_ramp=f"stop here — '{node.title}' stands alone; nothing is withheld "
                      "for leaving",
            depth_after=state.depth + 1)

    def consume(self, state: AudienceState, node_id: str) -> AudienceState:
        """Record actual consumption; recommendations follow consumption, never precede it."""
        if node_id not in self.nodes:
            raise RabbitHoleRefusal(f"unknown node {node_id!r}")
        state.consumed.append(node_id)
        return state
