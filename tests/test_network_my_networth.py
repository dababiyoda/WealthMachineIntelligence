from typing import Dict

from src.network_my_networth import NetworkWealthEngine


def test_portfolio_run_creates_reports() -> None:
    engine = NetworkWealthEngine(rules_path="automation/sample-rules.json")

    ventures: Dict[str, Dict[str, object]] = {
        "venture-alpha": {
            "technology_signals": [
                {"name": "Edge AI", "impact": 0.82, "maturity": 0.75, "theme": "AI"},
                {"name": "Automation", "impact": 0.78, "maturity": 0.7, "theme": "Ops"},
            ],
            "market_data": {"demand_index": 0.68, "growth_rate": 0.08, "competition_index": 0.4},
            "business_model": {"base_price": 119.0},
            "financial": {"minimum_roi": 0.6},
            "personas": ["Builders", "Operators"],
        },
        "venture-beta": {
            "technology_signals": [
                {"name": "Fintech APIs", "impact": 0.7, "maturity": 0.65, "theme": "Fintech"},
            ],
            "market_data": {"demand_index": 0.6, "growth_rate": 0.07, "competition_index": 0.5},
            "business_model": {"base_price": 89.0},
            "financial": {"minimum_roi": 0.55},
            "personas": ["Founders"],
            "industry": "fintech",
            "jurisdictions": ["US", "EU"],
        },
    }

    result = engine.run_portfolio(ventures)

    assert set(result.ventures.keys()) == set(ventures.keys())
    for report in result.ventures.values():
        venture = report["venture"]
        assert venture["go_no_go"] in {"go", "defer"}
        assert "risk" in venture
        assert report["team"]["insights"], "Team loop should generate insights for each venture"
        assert report["phase"]["decision"] in {"promote", "stabilize", "regress"}

    assert result.portfolio_summary, "Portfolio summary should be populated"
    assert result.performance_report.get("goals"), "SMART goal report should include goals"


def test_custom_rule_triggers_decision_outcome() -> None:
    risk_rule = NetworkWealthEngine.build_risk_rule(threshold=0.1)
    engine = NetworkWealthEngine(rules=[risk_rule])

    payload = {
        "technology_signals": [],
        "market_data": {"demand_index": 0.5, "growth_rate": 0.04, "competition_index": 0.55},
        "financial": {"minimum_roi": 0.2},
        "minimum_opportunity_score": 0.2,
    }

    report = engine.run_venture_sync("venture-risky", payload)
    decisions = report["venture"]["decision_outcomes"]

    assert decisions, "Decision engine should produce outcomes when guardrails trigger"
    assert any(outcome.get("action_type") == "update_venture_status" for outcome in decisions)
    assert report["venture"]["risk"]["risk_level"] in {"Ultra Low", "Low", "Moderate", "High", "Very High"}
    assert report["team"]["performance_snapshots"]
