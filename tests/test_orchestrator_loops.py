"""Integration tests for the Wealth Machine orchestrator."""

import asyncio
from typing import Dict

from src.services.orchestrator import WealthMachineOrchestrator


def test_income_stream_cycle_generates_cohesive_plan() -> None:
    orchestrator = WealthMachineOrchestrator()

    payload = {
        "technology_signals": [
            {"name": "AI Automation", "impact": 0.9, "maturity": 0.8, "theme": "AI"},
            {"name": "Low-code Platforms", "impact": 0.75, "maturity": 0.7, "theme": "Productivity"},
        ],
        "market_data": {
            "demand_index": 0.72,
            "growth_rate": 0.09,
            "competition_index": 0.45,
        },
        "business_model": {"base_price": 129.0},
        "financial": {"minimum_roi": 0.7},
        "minimum_opportunity_score": 0.6,
        "personas": ["Technical Founders", "Operators"],
        "venture_type": "DigitalVenture",
        "industry": "saas",
        "jurisdictions": ["US", "EU"],
    }

    report = asyncio.run(orchestrator.run_income_stream_cycle("venture-async-1", payload))

    venture = report["venture"]
    assert venture["go_no_go"] == "go"
    assert venture["opportunity"]["opportunity_score"] >= 0.6
    assert venture["financial"]["expected_roi"] >= payload["financial"]["minimum_roi"]
    assert venture["risk"]["risk_level"] in {"Ultra Low", "Low", "Moderate"}

    team = report["team"]
    assert team["insights"], "Team loop should generate collaboration insights"
    first_agent_snapshot = next(iter(team["performance_snapshots"].values()))
    assert first_agent_snapshot["goals"], "Performance tracker must return goal snapshots"


def test_orchestrator_runs_sync_event_loop() -> None:
    orchestrator = WealthMachineOrchestrator()

    async def _run() -> Dict[str, object]:
        return await orchestrator.run_income_stream_cycle("venture-sync-1", {
            "technology_signals": [],
            "market_data": {"demand_index": 0.55, "growth_rate": 0.04, "competition_index": 0.5},
            "financial": {"minimum_roi": 0.4},
        })

    loop = asyncio.new_event_loop()
    try:
        report = loop.run_until_complete(_run())
    finally:
        loop.close()
    assert set(report.keys()) == {"venture", "team"}
