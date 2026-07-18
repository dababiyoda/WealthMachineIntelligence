"""Risk management helper utilities.

The legacy simulation repository includes a ``RiskAssessmentService`` backed
by SQLAlchemy models. For local loop evaluation, this module also provides an
in-memory fallback so the simulation can run without a configured database. The
``RiskManager`` defined here delegates to the existing service when it
is available and otherwise returns a deterministic simulation heuristic.
The heuristic is an uncalibrated review index, not a failure probability,
and carries no authority to approve investment or another external action.
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
        risk_level = self._determine_risk_level(risk_score)
        recommendations = self._generate_recommendations(risk_level, metrics)

        return {
            "agent_id": "heuristic-risk-manager",
            "risk_score": risk_score,
            "heuristic_risk_index": risk_score,
            "market_risk": round(opportunity_component, 3),
            "operational_risk": round(execution_component, 3),
            "financial_risk": round(roi_component, 3),
            "technical_risk": round(buffer_component, 3),
            "risk_level": risk_level,
            "recommendations": recommendations,
            "evidence_status": "simulation_heuristic_unvalidated",
            "risk_semantics": "uncalibrated_heuristic_index_not_probability",
            "confidence_status": "not_calibrated",
            "authority": "recommendation_only",
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
            "Ultra Low": ["Prioritize external validation", "Document supporting and contradicting evidence"],
            "Low": ["Run a bounded evidence test", "Maintain standard review"],
            "Moderate": ["Reduce the largest uncertainty", "Add contingency review"],
            "High": ["Mitigate the dominant modeled factor", "Do not scale from this score"],
            "Very High": ["Recommend a hold", "Re-evaluate the underlying assumptions"],
        }
        return {
            "actions": base_actions[risk_level],
            "metrics": metrics,
            "authority": "recommendation_only",
        }


__all__ = ["RiskManager"]
