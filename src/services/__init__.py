"""Business logic services used by the API and agents.

The ``services`` package contains long-running classes that implement
the core algorithms for market intelligence, risk assessment and the
multi-agent orchestration stack.  Imports are intentionally lazy to
avoid initialising database connections during test collection.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking convenience only
    from .ai_agents import MarketIntelligenceService, RiskAssessmentService
    from .decision_engine import DecisionEngine
    from .orchestrator import WealthMachineOrchestrator
    from .risk_management import RiskManager

__all__ = [
    "MarketIntelligenceService",
    "RiskAssessmentService",
    "DecisionEngine",
    "WealthMachineOrchestrator",
    "RiskManager",
]