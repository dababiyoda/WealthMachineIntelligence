"""Performance tracking utilities for specialized agents.

This module introduces a lightweight framework for managing SMART
goals (Specific, Measurable, Achievable, Relevant and Time-bound)
across the multi-agent system.  The :class:`PerformanceTracker`
component keeps a registry of active goals for each agent, records
incremental progress updates and can generate compact summaries that
feed the Team Loop retrospectives.

The implementation deliberately avoids any external storage so it can
be used in automated tests or local experimentation environments.  In
production the tracker could synchronise with a database or analytics
layer, but the in-memory representation defined here provides enough
structure for orchestration logic to reason about performance trends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, DefaultDict, Dict, List, Optional

from collections import defaultdict


@dataclass
class SMARTGoal:
    """Represents a single SMART goal assignment.

    Parameters
    ----------
    goal_id:
        Globally unique identifier for the goal.
    agent_id:
        The identifier of the agent that owns the goal.
    description:
        Human readable description of the objective.
    specific, achievable, relevant:
        Narrative components of the SMART framework.
    measurable:
        Dictionary of metric names to target values used for
        quantitative evaluation.
    time_bound:
        Deadline for the goal.
    progress:
        Normalised progress ratio within ``[0, 1]``.
    history:
        Sequence of progress updates for auditing/feedback loops.
    """

    goal_id: str
    agent_id: str
    description: str
    specific: str
    measurable: Dict[str, float]
    achievable: str
    relevant: str
    time_bound: datetime
    progress: float = 0.0
    history: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        """Serialise goal metadata for reporting layers."""

        return {
            "goal_id": self.goal_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "specific": self.specific,
            "measurable": self.measurable,
            "achievable": self.achievable,
            "relevant": self.relevant,
            "time_bound": self.time_bound.isoformat(),
            "progress": round(self.progress, 3),
            "history": list(self.history),
        }


class PerformanceTracker:
    """Tracks SMART goals and progress for the agent network."""

    def __init__(self) -> None:
        self._goals: Dict[str, SMARTGoal] = {}
        self._agent_goals: DefaultDict[str, List[str]] = defaultdict(list)

    def register_goal(self, goal: SMARTGoal) -> SMARTGoal:
        """Register a new SMART goal or overwrite an existing one.

        Returns the registered goal to make call sites convenient for
        chaining.  If the goal already exists its progress is preserved
        but narrative fields are refreshed to reflect the latest
        definition.
        """

        existing = self._goals.get(goal.goal_id)
        if existing:
            goal.progress = existing.progress
            goal.history = list(existing.history)
        self._goals[goal.goal_id] = goal
        if goal.goal_id not in self._agent_goals[goal.agent_id]:
            self._agent_goals[goal.agent_id].append(goal.goal_id)
        return goal

    def get_goal(self, goal_id: str) -> Optional[SMARTGoal]:
        """Retrieve a goal by identifier."""

        return self._goals.get(goal_id)

    def record_progress(self, goal_id: str, increment: float, note: str = "") -> SMARTGoal:
        """Apply a progress increment to a goal.

        ``increment`` can be positive or negative but the internal
        progress counter is clamped to ``[0, 1]`` to maintain SMART
        semantics.  Each update is appended to the goal history with a
        timestamp for retrospective analysis.
        """

        goal = self._goals.get(goal_id)
        if not goal:
            raise KeyError(f"Goal {goal_id} is not registered")
        goal.progress = min(1.0, max(0.0, goal.progress + increment))
        goal.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "increment": increment,
            "note": note,
        })
        return goal

    def get_agent_goal_ids(self, agent_id: str) -> List[str]:
        """Return goal identifiers associated with an agent."""

        return list(self._agent_goals.get(agent_id, []))

    def get_primary_goal_id(self, agent_id: str) -> Optional[str]:
        """Convenience accessor for the first registered goal."""

        goal_ids = self.get_agent_goal_ids(agent_id)
        return goal_ids[0] if goal_ids else None

    def generate_report(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Produce a summary suitable for dashboards or retrospectives."""

        if agent_id is None:
            return {
                "goals": [goal.as_dict() for goal in self._goals.values()],
            }

        goal_ids = self.get_agent_goal_ids(agent_id)
        goals = [self._goals[gid].as_dict() for gid in goal_ids if gid in self._goals]
        return {
            "agent_id": agent_id,
            "goals": goals,
        }


__all__ = ["SMARTGoal", "PerformanceTracker"]

