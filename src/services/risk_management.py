"""Risk management helper utilities.

The production repository ships with an advanced
``RiskAssessmentService`` backed by SQLAlchemy models.  For the
autonomous Wealth Machine orchestration we also need an in-memory
fallback so the loops can execute without a configured database.  The
``RiskManager`` defined here delegates to the existing service when it
is available and gracefully degrades to a deterministic heuristic that
produces actionable metrics for decision making.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..core.knowledge_graph_connector import KnowledgeGraphConnector


class RiskManager:
    """Facade that blends deterministic risk scoring with stored assessments."""

    def __init__(self, risk_service: Optional[Any] = None, connector: Optional[KnowledgeGraphConnector] = None):
        self.risk_service = risk_service
        self.connector = connector or KnowledgeGraphConnector()

    async def assess(self, venture_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Return a risk profile and persist it through the connector."""

        assessment: Dict[str, Any]
        if self.risk_service is not None:
            try:
                assessment = await self.risk_service.assess_venture_risk(venture_id)
            except Exception:  # pragma: no cover - defensive guard for optional dependency
                assessment = self._heuristic_assessment(metrics)
        else:
            assessment = self._heuristic_assessment(metrics)

        self.connector.store_risk_assessment(venture_id, assessment)
        return assessment

    def _heuristic_assessment(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute a deterministic risk score from aggregate metrics."""

        opportunity_score = float(metrics.get("opportunity_score", 0.5))
        execution_confidence = float(metrics.get("execution_confidence", 0.5))
        expected_roi = float(metrics.get("expected_roi", 0.0))
        risk_buffer = float(metrics.get("risk_buffer", 0.1))

        # Higher opportunity, confidence and ROI reduce the risk factor.
        opportunity_component = (1 - opportunity_score) * 0.4
        execution_component = (1 - execution_confidence) * 0.35
        roi_component = max(0.0, 0.25 - min(expected_roi / 10, 0.25))
        buffer_component = max(0.0, 0.2 - risk_buffer) * 0.2

        risk_score = round(min(1.0, max(0.0, opportunity_component + execution_component + roi_component + buffer_component)), 3)
        failure_probability = round(min(1.0, risk_score * 0.55), 3)

        risk_level = self._determine_risk_level(risk_score)
        recommendations = self._generate_recommendations(risk_level, metrics)

        return {
            "agent_id": "heuristic-risk-manager",
            "risk_score": risk_score,
            "failure_probability": failure_probability,
            "market_risk": round(opportunity_component, 3),
            "operational_risk": round(execution_component, 3),
            "financial_risk": round(roi_component, 3),
            "technical_risk": round(buffer_component, 3),
            "risk_level": risk_level,
            "recommendations": recommendations,
            "confidence_level": 0.72,
            "model_version": "heuristic-1.0",
            "features_used": ["opportunity_score", "execution_confidence", "expected_roi", "risk_buffer"],
        }

    @staticmethod
    def _determine_risk_level(risk_score: float) -> str:
        if risk_score <= 0.2:
            return "Ultra Low"
        if risk_score <= 0.35:
            return "Low"
        if risk_score <= 0.5:
            return "Moderate"
        if risk_score <= 0.7:
            return "High"
        return "Very High"

    @staticmethod
    def _generate_recommendations(risk_level: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        base_actions = {
            "Ultra Low": ["Accelerate investment", "Document success patterns"],
            "Low": ["Proceed with standard oversight", "Share playbooks across ventures"],
            "Moderate": ["Proceed with caution", "Add contingency reviews"],
            "High": ["Mitigate key risks", "Delay scaling"],
            "Very High": ["Pause venture", "Re-evaluate fundamentals"],
        }
        return {
            "actions": base_actions[risk_level],
            "metrics": metrics,
        }


__all__ = ["RiskManager"]

