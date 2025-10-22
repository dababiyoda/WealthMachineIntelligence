"""Specialised agent implementations for the Wealth Machine orchestration.

Each agent inherits from :class:`~src.agents.base.BaseAgent` and
encapsulates domain specific heuristics that power the Income Streams
and Team loops.  The behaviours implemented here are intentionally
deterministic so they can be exercised in automated tests while still
mirroring the qualitative reasoning the human playbooks describe.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseAgent


@dataclass
class AgentOutput:
    """Container used by agents to report structured results."""

    summary: str
    data: Dict[str, Any]


class SpecializedAgent(BaseAgent):
    """Base class for specialised Wealth Machine agents."""

    role_name: str
    capabilities: List[str]

    def __init__(self, agent_id: str, agent_type: str, role_name: str, capabilities: Optional[List[str]] = None):
        super().__init__(agent_id=agent_id, agent_type=agent_type)
        self.role_name = role_name
        self.capabilities = capabilities or []
        self._collaboration_log: List[str] = []

    async def _setup_resources(self) -> None:  # pragma: no cover - trivial initialisation
        self.knowledge_base.setdefault("playbooks", [])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        """Handle a domain specific task and return an :class:`AgentOutput`."""

        return AgentOutput(summary=f"No-op task for {self.role_name}", data=task)

    async def handle_collaboration(self, context: Dict[str, Any]) -> Optional[str]:
        """Generate a qualitative insight for the Team Loop."""

        insight = f"{self.role_name} confirms readiness across {', '.join(self.capabilities[:2]) or 'core skills'}."
        self._collaboration_log.append(insight)
        return insight


class EmergingTechAgent(SpecializedAgent):
    """Identifies and qualifies technology-led opportunities."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "emerging_tech", "Emerging Technology Scout", ["trend mapping", "signal synthesis"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        signals = task.get("technology_signals", [])
        if signals:
            impact_scores = [float(signal.get("impact", 0.5)) for signal in signals]
            maturity_scores = [float(signal.get("maturity", 0.5)) for signal in signals]
            blended_score = (statistics.mean(impact_scores) * 0.6) + (statistics.mean(maturity_scores) * 0.4)
            blended_score = max(0.0, min(1.0, blended_score))
        else:
            blended_score = 0.3

        opportunity_score = round(min(1.0, 0.25 + blended_score * 0.65 + len(signals) * 0.03), 3)
        opportunities: List[Dict[str, Any]] = []
        for signal in signals:
            opportunities.append({
                "name": signal.get("name", "Unnamed Opportunity"),
                "confidence": round((float(signal.get("impact", 0.5)) + float(signal.get("maturity", 0.5))) / 2, 2),
                "theme": signal.get("theme", "General"),
            })

        summary = f"Identified {len(opportunities)} technology opportunities with score {opportunity_score}."
        data = {
            "opportunity_score": opportunity_score,
            "opportunities": opportunities,
            "signal_summary": {
                "average_impact": round(statistics.mean([float(s.get("impact", 0.0)) for s in signals]) if signals else 0.0, 3),
                "average_maturity": round(statistics.mean([float(s.get("maturity", 0.0)) for s in signals]) if signals else 0.0, 3),
            },
        }
        return AgentOutput(summary=summary, data=data)


class MarketAnalystAgent(SpecializedAgent):
    """Assesses market dynamics and commercial viability."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "market_analyst", "Market Analyst", ["market sizing", "competitive intelligence"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        market_data = task.get("market_data", {})
        demand_index = float(market_data.get("demand_index", 0.5))
        growth_rate = float(market_data.get("growth_rate", 0.05))
        competition = float(market_data.get("competition_index", 0.5))

        opportunity_score = float(task.get("opportunity_score", 0.5))
        market_alignment = round(min(1.0, (demand_index * 0.5) + (growth_rate * 5 * 0.3) + ((1 - competition) * 0.2)), 3)
        commercial_confidence = round((opportunity_score * 0.4) + (market_alignment * 0.6), 3)

        summary = f"Market alignment {market_alignment} with commercial confidence {commercial_confidence}."
        data = {
            "market_alignment": market_alignment,
            "commercial_confidence": commercial_confidence,
            "demand_index": demand_index,
            "growth_rate": growth_rate,
            "competition_index": competition,
        }
        return AgentOutput(summary=summary, data=data)


class ProductDevelopmentAgent(SpecializedAgent):
    """Crafts lean product delivery plans."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "product_dev", "Product Development", ["MVP design", "roadmapping"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        alignment = float(task.get("market_alignment", 0.5))
        opportunity_score = float(task.get("opportunity_score", 0.5))

        sprint_count = max(2, int(round(6 - alignment * 3)))
        execution_confidence = round(min(1.0, 0.45 + opportunity_score * 0.35 + alignment * 0.2), 3)
        roadmap = [
            {"phase": "Discovery", "duration_weeks": 2},
            {"phase": "MVP Build", "duration_weeks": sprint_count},
            {"phase": "Pilot", "duration_weeks": 2},
        ]

        summary = f"Structured {len(roadmap)}-phase delivery with confidence {execution_confidence}."
        data = {
            "execution_confidence": execution_confidence,
            "roadmap": roadmap,
            "sprint_count": sprint_count,
        }
        return AgentOutput(summary=summary, data=data)


class BusinessModelInnovatorAgent(SpecializedAgent):
    """Designs revenue and pricing mechanics."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "business_model", "Business Model Innovator", ["pricing", "unit economics"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        demand_index = float(task.get("demand_index", 0.5))
        growth_rate = float(task.get("growth_rate", 0.05))
        base_price = float(task.get("base_price", 49.0))

        price_multiplier = 1 + (growth_rate * 2) + ((demand_index - 0.5) * 0.4)
        pricing_strategy = round(base_price * max(0.6, price_multiplier), 2)
        recurring_revenue_ratio = round(min(1.0, 0.5 + demand_index * 0.4), 3)

        summary = f"Defined pricing at {pricing_strategy} with recurring ratio {recurring_revenue_ratio}."
        data = {
            "pricing": pricing_strategy,
            "recurring_revenue_ratio": recurring_revenue_ratio,
            "revenue_streams": [
                {"type": "subscription", "ratio": recurring_revenue_ratio},
                {"type": "services", "ratio": round(1 - recurring_revenue_ratio, 3)},
            ],
        }
        return AgentOutput(summary=summary, data=data)


class FinancialStrategistAgent(SpecializedAgent):
    """Plans capital allocation and ROI projections."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "financial_strategist", "Financial Strategist", ["budgeting", "risk buffers"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        roadmap = task.get("roadmap", [])
        recurring_ratio = float(task.get("recurring_revenue_ratio", 0.6))
        pricing = float(task.get("pricing", 49.0))

        duration_weeks = sum(step.get("duration_weeks", 0) for step in roadmap)
        development_cost = max(10000.0, duration_weeks * 3500.0)
        expected_roi = round((pricing * recurring_ratio * 18) / (development_cost / 1000), 3)
        risk_buffer = round(min(0.5, 0.15 + recurring_ratio * 0.2), 3)

        summary = f"Projected ROI {expected_roi} with contingency buffer {risk_buffer}."
        data = {
            "development_cost": round(development_cost, 2),
            "expected_roi": expected_roi,
            "risk_buffer": risk_buffer,
            "runway_months": max(3, int(duration_weeks / 4) + 1),
        }
        return AgentOutput(summary=summary, data=data)


class LegalCounselAgent(SpecializedAgent):
    """Monitors compliance and launch readiness."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "legal", "Legal Counsel", ["compliance", "risk mitigation"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        industry = task.get("industry", "general")
        jurisdictions = task.get("jurisdictions", ["US"])
        risk_level = task.get("risk_level", "Moderate")

        checklist = [
            "Review data protection obligations",
            "Validate contract templates",
            "Confirm licensing requirements",
        ]
        if industry.lower() == "fintech":
            checklist.append("Align with financial regulations (KYC/AML)")

        readiness = "go" if risk_level in {"Ultra Low", "Low", "Moderate"} else "hold"
        summary = f"Compliance readiness is {readiness} across {len(jurisdictions)} jurisdictions."
        data = {
            "readiness": readiness,
            "checklist": checklist,
            "jurisdictions": jurisdictions,
        }
        return AgentOutput(summary=summary, data=data)


class MarketingAgent(SpecializedAgent):
    """Crafts growth and go-to-market campaigns."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "marketing", "Marketing Strategist", ["funnel design", "community"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        target_personas = task.get("personas", ["General Innovators"])
        demand_index = float(task.get("demand_index", 0.5))
        opportunity_score = float(task.get("opportunity_score", 0.5))

        channel_focus = ["Content", "Partnerships"] if demand_index > 0.6 else ["Education", "Ads"]
        activation_score = round(min(1.0, 0.4 + opportunity_score * 0.4 + demand_index * 0.2), 3)

        summary = f"Activation score {activation_score} across {len(channel_focus)} channels."
        data = {
            "activation_score": activation_score,
            "channels": channel_focus,
            "personas": target_personas,
        }
        return AgentOutput(summary=summary, data=data)


class NetworkingAgent(SpecializedAgent):
    """Coordinates ecosystem leverage and reinvestment options."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "networking", "Strategic Partnerships", ["alliances", "capital recycling"])

    async def handle_task(self, task: Dict[str, Any]) -> AgentOutput:
        opportunities = task.get("opportunities", [])
        activation_score = float(task.get("activation_score", 0.5))
        recurring_ratio = float(task.get("recurring_revenue_ratio", 0.5))

        partners = []
        for opportunity in opportunities[:3]:
            partners.append({
                "name": opportunity.get("name", "Partner"),
                "expected_value": round(activation_score * opportunity.get("confidence", 0.5) * 10000, 2),
            })

        reinvestment_rate = round(min(0.6, 0.2 + recurring_ratio * 0.35), 3)
        summary = f"Prepared {len(partners)} partnerships with reinvestment rate {reinvestment_rate}."
        data = {
            "partners": partners,
            "reinvestment_rate": reinvestment_rate,
        }
        return AgentOutput(summary=summary, data=data)


__all__ = [
    "AgentOutput",
    "SpecializedAgent",
    "EmergingTechAgent",
    "MarketAnalystAgent",
    "ProductDevelopmentAgent",
    "BusinessModelInnovatorAgent",
    "FinancialStrategistAgent",
    "LegalCounselAgent",
    "MarketingAgent",
    "NetworkingAgent",
]

