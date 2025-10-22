"""High level orchestrator for the Wealth Machine."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

from ..agents.specialized import (
    BusinessModelInnovatorAgent,
    EmergingTechAgent,
    FinancialStrategistAgent,
    LegalCounselAgent,
    MarketAnalystAgent,
    MarketingAgent,
    NetworkingAgent,
    ProductDevelopmentAgent,
)
from ..core.loops import IncomeStreamsLoop, TeamLoop
from ..core.performance import PerformanceTracker, SMARTGoal
from ..services.decision_engine import DecisionEngine
from ..services.risk_management import RiskManager


class WealthMachineOrchestrator:
    """Coordinates agents, loops and decisioning for venture execution."""

    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        risk_manager: Optional[RiskManager] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
    ) -> None:
        self.agents = {
            "emerging_tech": EmergingTechAgent("agent-emerging-tech"),
            "market_analyst": MarketAnalystAgent("agent-market-analyst"),
            "product_dev": ProductDevelopmentAgent("agent-product-dev"),
            "business_model": BusinessModelInnovatorAgent("agent-business-model"),
            "financial_strategist": FinancialStrategistAgent("agent-finance"),
            "legal": LegalCounselAgent("agent-legal"),
            "marketing": MarketingAgent("agent-marketing"),
            "networking": NetworkingAgent("agent-networking"),
        }

        self.performance_tracker = performance_tracker or PerformanceTracker()
        self._bootstrap_goals()

        self.decision_engine = decision_engine or DecisionEngine([])
        self.risk_manager = risk_manager or RiskManager()

        self.income_loop = IncomeStreamsLoop(
            self.agents,
            decision_engine=self.decision_engine,
            risk_manager=self.risk_manager,
            performance_tracker=self.performance_tracker,
        )
        self.team_loop = TeamLoop(self.agents, self.performance_tracker)

    def _bootstrap_goals(self) -> None:
        """Create baseline SMART goals for each agent."""

        for key, agent in self.agents.items():
            goal = SMARTGoal(
                goal_id=f"goal-{agent.agent_id}",
                agent_id=agent.agent_id,
                description=f"Maintain high leverage output for {key} role",
                specific="Deliver actionable insights every cycle",
                measurable={"cycles": 12},
                achievable="Calibrated to weekly cadences",
                relevant="Directly supports venture throughput",
                time_bound=datetime.utcnow() + timedelta(days=90),
            )
            self.performance_tracker.register_goal(goal)

    async def run_income_stream_cycle(self, venture_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute both loops for a venture and return a consolidated report."""

        cycle_result = await self.income_loop.execute_cycle(venture_id, payload)
        team_result = await self.team_loop.execute_cycle(cycle_result)

        return {
            "venture": cycle_result.as_dict(),
            "team": team_result.as_dict(),
        }


__all__ = ["WealthMachineOrchestrator"]

