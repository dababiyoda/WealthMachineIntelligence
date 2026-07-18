"""Heuristic risk-screening helper utilities.

The production repository ships with an advanced
``RiskAssessmentService`` backed by SQLAlchemy models.  For the
autonomous Wealth Machine orchestration we also need an in-memory
fallback so the loops can execute without a configured database.  The
``RiskManager`` defined here delegates to the existing service when it
is available and otherwise produces an uncalibrated deterministic score.
The score supports hypothesis screening; it is not a failure probability,
investment approval, or autonomy evidence.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..control.gateway import ExecutionGateway
from ..control.graph_adapter import GraphIntentClient
from ..core.knowledge_graph_connector import KnowledgeGraphConnector


class RiskManager:
    """Facade that blends deterministic risk scoring with stored assessments."""

    def __init__(
        self,
        risk_service: Optional[Any] = None,
        connector: Optional[KnowledgeGraphConnector] = None,
        gateway: Optional[ExecutionGateway] = None,
        context_fingerprint: str = "",
        agent_id: str = "risk-manager",
    ):
        self.risk_service = risk_service
        self.connector = connector or KnowledgeGraphConnector()
        self.graph_intents = GraphIntentClient(
            gateway,
            agent_id=agent_id,
            context_fingerprint=context_fingerprint,
        )

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

        assessment["persistence"] = self.graph_intents.submit(
            "persist_risk_assessment",
            venture_id,
            {
                "assessment": dict(assessment),
                "provenance": {
                    "producer": self.graph_intents.agent_id,
                    "source_type": (
                        "optional_risk_service"
                        if self.risk_service is not None
                        else "deterministic_heuristic"
                    ),
                    "probability_calibrated": bool(
                        assessment.get("probability_calibrated", False)
                    ),
                },
            },
        )
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
            "probability_calibrated": False,
            "score_semantics": "heuristic screening score; external validation required",
            "execution_authority": False,
        }

    @staticmethod
    def _determine_risk_level(risk_score: float) -> str:
        if risk_score <= 0.2:
            return "Low"
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
            "Ultra Low": ["Validate externally", "Document the evidence trail"],
            "Low": ["Run a bounded validation test", "Document the evidence trail"],
            "Moderate": ["Proceed with caution", "Add contingency reviews"],
            "High": ["Mitigate key risks", "Delay scaling"],
            "Very High": ["Pause venture", "Re-evaluate fundamentals"],
        }
        return {
            "actions": base_actions[risk_level],
            "metrics": metrics,
        }


__all__ = ["RiskManager"]
