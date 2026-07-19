"""Prevent prototype scores from turning into autonomous investment claims."""

import pytest

from src.services.ai_agents import (
    DecisionOrchestrator,
    MarketIntelligenceService,
    RiskAssessmentService,
)


def test_high_synthetic_opportunity_only_proposes_bounded_validation() -> None:
    recommendations = MarketIntelligenceService()._generate_recommendations(0.95)
    combined = " ".join(recommendations).lower()
    assert "full investment" not in combined
    assert "human review" in combined
    assert "capital" in combined


def test_decision_orchestrator_never_returns_execution_authority() -> None:
    orchestrator = DecisionOrchestrator()
    decision = orchestrator._generate_final_decision(
        {"opportunity_score": 0.95},
        {"risk_score": 0.1},
    )
    assert decision["action"] == "PROPOSE_BOUNDED_PILOT"
    assert decision["requires_human_approval"] is True
    assert decision["execution_authority"] is False
    assert decision["probability_calibrated"] is False


def test_risk_probability_shape_is_explicitly_uncalibrated() -> None:
    service = RiskAssessmentService()
    proxy = service._convert_risk_to_probability(0.2)
    assert proxy == pytest.approx(0.004)
    assert service.legacy_score_threshold == 0.0001
