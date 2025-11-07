"""Income Streams and Team Loop implementations.

The master plan describes two reinforcing feedback loops.  This module
codifies both loops so they can be executed programmatically:

* :class:`IncomeStreamsLoop` orchestrates opportunity scouting through
  venture launch decisions.
* :class:`TeamLoop` ensures learnings and SMART goal progress are
  recycled back into the agent network.

Both loops are intentionally data driven yet deterministic, enabling
unit tests to verify behaviour without stochasticity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from .knowledge_graph_connector import KnowledgeGraphConnector
from .performance import PerformanceTracker
from ..agents.specialized import (
    AgentOutput,
    BusinessModelInnovatorAgent,
    EmergingTechAgent,
    FinancialStrategistAgent,
    LegalCounselAgent,
    MarketAnalystAgent,
    MarketingAgent,
    NetworkingAgent,
    ProductDevelopmentAgent,
)
from ..services.decision_engine import DecisionEngine
from ..services.risk_management import RiskManager


@dataclass
class VentureCycleResult:
    venture_id: str
    opportunity: AgentOutput
    market: AgentOutput
    product: AgentOutput
    business_model: AgentOutput
    financial: AgentOutput
    legal: AgentOutput
    marketing: AgentOutput
    partnerships: AgentOutput
    risk: Dict[str, Any]
    decision_outcomes: List[Dict[str, Any]]
    go_no_go: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "venture_id": self.venture_id,
            "opportunity": self.opportunity.data,
            "market": self.market.data,
            "product": self.product.data,
            "business_model": self.business_model.data,
            "financial": self.financial.data,
            "legal": self.legal.data,
            "marketing": self.marketing.data,
            "partnerships": self.partnerships.data,
            "risk": self.risk,
            "decision_outcomes": self.decision_outcomes,
            "go_no_go": self.go_no_go,
        }


class IncomeStreamsLoop:
    """Implements the Income Streams loop."""

    def __init__(
        self,
        agents: Mapping[str, Any],
        decision_engine: DecisionEngine,
        risk_manager: RiskManager,
        performance_tracker: PerformanceTracker,
        connector: Optional[KnowledgeGraphConnector] = None,
    ) -> None:
        self.agents = agents
        self.decision_engine = decision_engine
        self.risk_manager = risk_manager
        self.performance_tracker = performance_tracker
        self.connector = connector or KnowledgeGraphConnector()

    async def execute_cycle(self, venture_id: str, payload: Dict[str, Any]) -> VentureCycleResult:
        """Run a full venture evaluation cycle."""

        opportunity_agent: EmergingTechAgent = self.agents["emerging_tech"]
        market_agent: MarketAnalystAgent = self.agents["market_analyst"]
        product_agent: ProductDevelopmentAgent = self.agents["product_dev"]
        business_agent: BusinessModelInnovatorAgent = self.agents["business_model"]
        financial_agent: FinancialStrategistAgent = self.agents["financial_strategist"]
        legal_agent: LegalCounselAgent = self.agents["legal"]
        marketing_agent: MarketingAgent = self.agents["marketing"]
        networking_agent: NetworkingAgent = self.agents["networking"]

        opportunity = await opportunity_agent.handle_task({
            "technology_signals": payload.get("technology_signals", []),
        })
        self.connector.update_opportunities(venture_id, opportunity.data.get("opportunities", []))

        market = await market_agent.handle_task({
            "market_data": payload.get("market_data", {}),
            "opportunity_score": opportunity.data["opportunity_score"],
        })

        product = await product_agent.handle_task({
            "market_alignment": market.data["market_alignment"],
            "opportunity_score": opportunity.data["opportunity_score"],
        })

        business_model = await business_agent.handle_task({
            "demand_index": market.data["demand_index"],
            "growth_rate": market.data["growth_rate"],
            "base_price": payload.get("business_model", {}).get("base_price", 79.0),
        })

        financial = await financial_agent.handle_task({
            "roadmap": product.data["roadmap"],
            "recurring_revenue_ratio": business_model.data["recurring_revenue_ratio"],
            "pricing": business_model.data["pricing"],
        })

        legal = await legal_agent.handle_task({
            "industry": payload.get("industry", "general"),
            "jurisdictions": payload.get("jurisdictions", ["US"]),
            "risk_level": payload.get("risk_appetite", "Moderate"),
        })

        marketing = await marketing_agent.handle_task({
            "personas": payload.get("personas", ["Builders"]),
            "demand_index": market.data["demand_index"],
            "opportunity_score": opportunity.data["opportunity_score"],
        })

        partnerships = await networking_agent.handle_task({
            "opportunities": opportunity.data.get("opportunities", []),
            "activation_score": marketing.data["activation_score"],
            "recurring_revenue_ratio": business_model.data["recurring_revenue_ratio"],
        })

        metrics = {
            "opportunity_score": opportunity.data["opportunity_score"],
            "execution_confidence": product.data["execution_confidence"],
            "expected_roi": financial.data["expected_roi"],
            "risk_buffer": financial.data["risk_buffer"],
        }

        self.connector.update_venture_metrics(venture_id, {
            "opportunity_score": metrics["opportunity_score"],
            "market_alignment": market.data["market_alignment"],
            "expected_roi": metrics["expected_roi"],
        })

        risk = await self.risk_manager.assess(venture_id, metrics)
        decision_outcomes = self.decision_engine.evaluate(
            venture_id,
            payload.get("venture_type", "DigitalVenture"),
            {**metrics, "risk_score": risk.get("risk_score", 0.0)},
        )

        go_threshold = payload.get("financial", {}).get("minimum_roi", 0.5)
        go_no_go = "go" if (
            metrics["opportunity_score"] >= payload.get("minimum_opportunity_score", 0.55)
            and metrics["expected_roi"] >= go_threshold
            and risk.get("risk_level") in {"Ultra Low", "Low", "Moderate"}
        ) else "defer"

        return VentureCycleResult(
            venture_id=venture_id,
            opportunity=opportunity,
            market=market,
            product=product,
            business_model=business_model,
            financial=financial,
            legal=legal,
            marketing=marketing,
            partnerships=partnerships,
            risk=risk,
            decision_outcomes=decision_outcomes,
            go_no_go=go_no_go,
        )


@dataclass
class TeamCycleResult:
    insights: List[str]
    performance_snapshots: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "insights": self.insights,
            "performance_snapshots": self.performance_snapshots,
        }


class TeamLoop:
    """Facilitates knowledge sharing and continuous improvement."""

    def __init__(self, agents: Mapping[str, Any], performance_tracker: PerformanceTracker):
        self.agents = agents
        self.performance_tracker = performance_tracker

    async def execute_cycle(self, venture_result: VentureCycleResult) -> TeamCycleResult:
        insights: List[str] = []

        for agent_key, agent in self.agents.items():
            context = {
                "venture_id": venture_result.venture_id,
                "go_no_go": venture_result.go_no_go,
                "risk_level": venture_result.risk.get("risk_level"),
            }
            insight = await agent.handle_collaboration(context)
            if insight:
                insights.append(insight)

            goal_id = self.performance_tracker.get_primary_goal_id(agent.agent_id)
            if goal_id:
                increment = 0.05 if venture_result.go_no_go == "go" else 0.02
                note = f"Cycle outcome: {venture_result.go_no_go}, risk {venture_result.risk.get('risk_level')}"
                self.performance_tracker.record_progress(goal_id, increment, note=note)

        snapshots = {
            agent_key: self.performance_tracker.generate_report(agent.agent_id)
            for agent_key, agent in self.agents.items()
        }

        return TeamCycleResult(insights=insights, performance_snapshots=snapshots)


__all__ = [
    "IncomeStreamsLoop",
    "TeamLoop",
    "VentureCycleResult",
    "TeamCycleResult",
]

