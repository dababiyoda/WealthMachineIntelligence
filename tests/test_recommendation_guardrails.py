"""Prevent prototype scores from turning into autonomous investment claims."""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

import src.services.ai_agents as ai_agents_module
from src.database.models import VentureStatus
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


def test_synthetic_market_analysis_is_proposal_only_by_default() -> None:
    result = asyncio.run(
        MarketIntelligenceService().analyze_market_opportunity(
            "market-proposal-only",
            {
                "market_size": 1_000_000,
                "competition_level": "medium",
                "growth_rate": 0.1,
            },
        )
    )
    assert result["analysis_mode"] == "synthetic_demo"
    assert result["persistence"]["execution_status"] == "proposed"
    assert result["execution_authority"] is False


def test_risk_service_reads_but_does_not_write_or_mint_agent(monkeypatch) -> None:
    venture = SimpleNamespace(
        venture_type=SimpleNamespace(value="saas"),
        status=VentureStatus.IDEATION,
        automation_level=0.2,
        monthly_revenue=100.0,
        monthly_expenses=50.0,
    )

    class ReadOnlySession:
        def query(self, model):
            return self

        def filter(self, *args):
            return self

        def first(self):
            return venture

        def add(self, value):
            raise AssertionError("risk analysis must not write directly")

        def commit(self):
            raise AssertionError("risk analysis must not commit directly")

    @contextmanager
    def read_only_db():
        yield ReadOnlySession()

    monkeypatch.setattr(ai_agents_module, "get_db", read_only_db)
    service = RiskAssessmentService()
    result = asyncio.run(service.assess_venture_risk("risk-proposal-only"))

    assert result["persistence"]["execution_status"] == "proposed"
    assert result["execution_authority"] is False
    assert not hasattr(service, "_get_agent_id")
