"""Phase management utilities for orchestrating venture scale."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


RISK_ORDER = ["Ultra Low", "Low", "Moderate", "High", "Very High"]


@dataclass
class PhaseGate:
    """Represents a single phase with entry criteria and guardrails."""

    name: str
    minimum_opportunity_score: float
    minimum_expected_roi: float
    maximum_risk_level: str
    reinvestment_rate: float
    description: str = ""

    def allows(self, metrics: Dict[str, Any], risk_level: str) -> bool:
        """Return True if metrics satisfy the gate criteria."""

        risk_level = risk_level or "Moderate"
        try:
            current_risk_rank = RISK_ORDER.index(risk_level)
        except ValueError:
            current_risk_rank = len(RISK_ORDER) - 1
        risk_ok = current_risk_rank <= RISK_ORDER.index(self.maximum_risk_level)
        return (
            metrics.get("opportunity_score", 0.0) >= self.minimum_opportunity_score
            and metrics.get("expected_roi", 0.0) >= self.minimum_expected_roi
            and risk_ok
        )


@dataclass
class PhaseDecision:
    """Outcome of evaluating a venture against the phase gates."""

    venture_id: str
    current_phase: str
    decision: str
    reinvestment_rate: float
    next_phase: Optional[str] = None
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "venture_id": self.venture_id,
            "current_phase": self.current_phase,
            "next_phase": self.next_phase,
            "decision": self.decision,
            "reinvestment_rate": round(self.reinvestment_rate, 3),
            "reasons": list(self.reasons),
        }


class PhaseManager:
    """Determines how ventures progress across phases 1–3."""

    def __init__(self, phases: Optional[List[PhaseGate]] = None) -> None:
        self.phases = phases or [
            PhaseGate(
                name="Phase 1: Explore",
                minimum_opportunity_score=0.45,
                minimum_expected_roi=0.25,
                maximum_risk_level="High",
                reinvestment_rate=0.2,
                description="Small, low-risk experiments",
            ),
            PhaseGate(
                name="Phase 2: Validate",
                minimum_opportunity_score=0.6,
                minimum_expected_roi=0.45,
                maximum_risk_level="Moderate",
                reinvestment_rate=0.35,
                description="Validated bets ready for structured pilots",
            ),
            PhaseGate(
                name="Phase 3: Scale",
                minimum_opportunity_score=0.7,
                minimum_expected_roi=0.7,
                maximum_risk_level="Low",
                reinvestment_rate=0.5,
                description="Scaling portfolio with disciplined reinvestment",
            ),
        ]
        self._venture_phase: Dict[str, str] = {}
        self._history: Dict[str, List[PhaseDecision]] = {}

    def _current_index(self, venture_id: str) -> int:
        current = self._venture_phase.get(venture_id, self.phases[0].name)
        for idx, phase in enumerate(self.phases):
            if phase.name == current:
                return idx
        return 0

    def record_cycle(self, venture_id: str, metrics: Dict[str, Any], risk_level: str) -> PhaseDecision:
        """Evaluate a venture and return the recommended phase posture."""

        current_index = self._current_index(venture_id)
        current_phase = self.phases[current_index]
        reasons: List[str] = []
        decision = "stabilize"
        next_phase: Optional[str] = None

        # Promotion logic
        if current_index + 1 < len(self.phases):
            candidate_phase = self.phases[current_index + 1]
            if candidate_phase.allows(metrics, risk_level):
                decision = "promote"
                next_phase = candidate_phase.name
                self._venture_phase[venture_id] = candidate_phase.name
                reasons.append("Metrics satisfy next phase gate")

        # Regression logic if risk is too high for current phase
        if decision == "stabilize" and not current_phase.allows(metrics, risk_level) and current_index > 0:
            previous_phase = self.phases[current_index - 1]
            decision = "regress"
            next_phase = previous_phase.name
            self._venture_phase[venture_id] = previous_phase.name
            reasons.append("Risk or metrics breached current gate")

        # Maintain current state if no transition occurred
        if self._venture_phase.get(venture_id) is None:
            self._venture_phase[venture_id] = current_phase.name

        reinvestment_rate = self.phases[self._current_index(venture_id)].reinvestment_rate
        outcome = PhaseDecision(
            venture_id=venture_id,
            current_phase=current_phase.name,
            decision=decision,
            reinvestment_rate=reinvestment_rate,
            next_phase=next_phase,
            reasons=reasons,
        )
        self._history.setdefault(venture_id, []).append(outcome)
        return outcome

    def portfolio_summary(self) -> Dict[str, Any]:
        """Return current phase posture and last decision per venture."""

        return {
            venture_id: {
                "phase": self._venture_phase.get(venture_id, self.phases[0].name),
                "last_decision": self._history[venture_id][-1].as_dict() if self._history.get(venture_id) else None,
            }
            for venture_id in self._venture_phase
        }

    def history(self, venture_id: str) -> List[Dict[str, Any]]:
        """Return serialised decision history for a venture."""

        return [decision.as_dict() for decision in self._history.get(venture_id, [])]


__all__ = ["PhaseGate", "PhaseDecision", "PhaseManager"]
