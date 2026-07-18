"""End-to-end orchestration for the "My Network" wealth engine.

The :class:`NetworkWealthEngine` class wires together the Income Streams
Loop and Team Loop, the risk manager, decision rules, and phase gates so
that a local operator can simulate how a portfolio of ventures would be
sourced, validated, launched, and continuously improved.

The design intentionally mirrors the master plan:

* Specialized agents from :mod:`src.agents.specialized` scout
  opportunities, validate markets, design products, and handle go-to-
  market and partnerships.
* The Income Streams Loop turns raw signals into a coherent venture plan
  with ROI, risk, and go/no-go recommendations.
* The Team Loop shares insights back across the network while updating
  SMART goal progress so performance compounds over time.
* The risk manager and rule engine enforce guardrails, while the
  :class:`~src.services.phase_management.PhaseManager` scales ventures
  through phases 1–3 with explicit reinvestment controls.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

from src.control.gateway import ExecutionGateway
from src.core.knowledge_graph_connector import KnowledgeGraphConnector
from src.core.performance import PerformanceTracker, SMARTGoal
from src.services.decision_engine import (
    ActionSpec,
    ConditionNode,
    DecisionEngine,
    Operator,
    Rule,
)
from src.services.orchestrator import WealthMachineOrchestrator
from src.services.phase_management import PhaseManager
from src.services.risk_management import RiskManager


@dataclass
class PortfolioRunResult:
    """Container capturing the outcome of a portfolio-wide simulation."""

    ventures: Dict[str, Dict[str, Any]]
    portfolio_summary: Dict[str, Any]
    performance_report: Dict[str, Any]


class NetworkWealthEngine:
    """High-level facade that operationalises the master plan."""

    def __init__(
        self,
        rules_path: Optional[str] = None,
        rules: Optional[Iterable[Rule]] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
        phase_manager: Optional[PhaseManager] = None,
        connector: Optional[KnowledgeGraphConnector] = None,
        gateway: Optional[ExecutionGateway] = None,
        control_context_fingerprint: str = "",
    ) -> None:
        self.connector = connector or KnowledgeGraphConnector()
        self.performance_tracker = performance_tracker or PerformanceTracker()
        self.phase_manager = phase_manager or PhaseManager()

        if rules is not None:
            rule_list = list(rules)
            self.decision_engine = DecisionEngine(
                rule_list,
                connector=self.connector,
                gateway=gateway,
                context_fingerprint=control_context_fingerprint,
            )
        elif rules_path:
            self.decision_engine = DecisionEngine.from_json_file(
                rules_path,
                connector=self.connector,
                gateway=gateway,
                context_fingerprint=control_context_fingerprint,
            )
        else:
            self.decision_engine = DecisionEngine(
                [],
                connector=self.connector,
                gateway=gateway,
                context_fingerprint=control_context_fingerprint,
            )

        self.risk_manager = RiskManager(
            connector=self.connector,
            gateway=gateway,
            context_fingerprint=control_context_fingerprint,
        )
        self.orchestrator = WealthMachineOrchestrator(
            decision_engine=self.decision_engine,
            risk_manager=self.risk_manager,
            performance_tracker=self.performance_tracker,
            phase_manager=self.phase_manager,
        )

    def register_goal(self, goal: SMARTGoal) -> SMARTGoal:
        """Register a SMART goal for any agent in the network."""

        return self.performance_tracker.register_goal(goal)

    async def run_venture(self, venture_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute both loops for a single venture asynchronously."""

        return await self.orchestrator.run_income_stream_cycle(venture_id, payload)

    def run_venture_sync(self, venture_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for environments without an event loop."""

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.run_venture(venture_id, payload))
        finally:
            loop.close()

    def run_portfolio(self, ventures: Mapping[str, Dict[str, Any]]) -> PortfolioRunResult:
        """Run a full cycle across multiple ventures."""

        reports: Dict[str, Dict[str, Any]] = {}
        for venture_id, payload in ventures.items():
            reports[venture_id] = self.run_venture_sync(venture_id, payload)

        return PortfolioRunResult(
            ventures=reports,
            portfolio_summary=self.phase_manager.portfolio_summary(),
            performance_report=self.performance_tracker.generate_report(),
        )

    @staticmethod
    def build_risk_rule(rule_id: str = "risk_guardrail", threshold: float = 0.65) -> Rule:
        """Convenience helper to create a risk-based decision rule."""

        condition = ConditionNode(
            metric="risk_score",
            comparator=Operator.GREATER_THAN,
            value=threshold,
        )
        action = ActionSpec(
            type="update_venture_status",
            parameters={
                "new_status": "High Risk",
                "notify_roles": ["RiskManager"],
            },
        )
        return Rule(
            rule_id=rule_id,
            name="Risk Threshold Guardrail",
            venture_type="DigitalVenture",
            condition=condition,
            action=action,
        )


__all__ = ["NetworkWealthEngine", "PortfolioRunResult"]
