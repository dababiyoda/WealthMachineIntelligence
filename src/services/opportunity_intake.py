"""Intake for DALEOBANKS OpportunityPackets.

The flow: an OpportunityPacket arrives on the wire, is validated as data,
adapted into the payload the existing :class:`NetworkWealthEngine` venture
loop expects, run through the full agent cycle (opportunity scoring, market,
product, business model, financial, legal, marketing, partnerships, risk),
and mapped back into a VentureAssessment wire payload.

Hardcoded guardrails (not configuration):

* ``requires_human_approval`` is always true — an assessment is a
  recommendation, never an execution. Inbound attempts to unset it are
  ignored.
* Packets carrying legal risk flags are killed and escalated; the engine's
  scores are reported for context but never override the escalation.
* Packets with no evidence come back ``needs_more_evidence``.
* Finance-flagged packets always require legal review and carry the
  educational-content-only reason. No revenue promises appear anywhere.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from src.network_my_networth.system import NetworkWealthEngine
from src.services.adversarial import build_cases, severe_unresolved
from src.services.venture_protocol import (
    FINANCE_EDUCATION_FLAG,
    LEGAL_RISK_FLAGS,
    SCHEMA_VERSION,
    validate_assessment_wire,
    validate_packet_wire,
)

logger = logging.getLogger(__name__)

_URGENCY_IMPACT = {"high": 0.8, "medium": 0.65, "low": 0.5}
_URGENCY_DEMAND = {"high": 0.75, "medium": 0.6, "low": 0.45}
# Low-urgency signals must clear a higher bar before they earn attention.
_URGENCY_MIN_SCORE = {"high": 0.5, "medium": 0.55, "low": 0.65}
_MAX_SIGNALS = 5


def packet_to_engine_payload(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a validated OpportunityPacket into the venture-loop payload."""
    urgency = packet["urgency"]
    impact = _URGENCY_IMPACT[urgency]
    maturity = round(0.35 + 0.5 * packet["confidence"], 3)
    name = (packet["possible_offer"] or packet["core_thesis"] or "Unnamed opportunity")[:60]

    signals = [
        {
            "name": name,
            "impact": impact,
            "maturity": maturity,
            "theme": packet["signal_type"],
            "evidence": evidence_item,
        }
        for evidence_item in packet["evidence"][:_MAX_SIGNALS]
    ]

    finance = FINANCE_EDUCATION_FLAG in packet["risk_flags"]
    legal_flagged = bool(LEGAL_RISK_FLAGS & set(packet["risk_flags"]))

    return {
        "technology_signals": signals,
        "market_data": {
            "demand_index": _URGENCY_DEMAND[urgency],
            "growth_rate": 0.06,
            "competition_index": 0.5,
        },
        "business_model": {"base_price": 29.0},
        "industry": "financial_education" if finance else "general",
        "jurisdictions": ["US"],
        "risk_appetite": "High" if legal_flagged else "Moderate",
        "personas": [packet["customer_segment"] or packet["audience"] or "General"],
        "minimum_opportunity_score": _URGENCY_MIN_SCORE[urgency],
        "venture_type": "DigitalVenture",
    }


class OpportunityIntakeService:
    """Validates packets, runs the venture loop, returns assessments."""

    def __init__(self, engine: Optional[NetworkWealthEngine] = None) -> None:
        self.engine = engine or NetworkWealthEngine(
            rules=[NetworkWealthEngine.build_risk_rule()]
        )
        self._assessments: Dict[str, Dict[str, Any]] = {}
        self._by_packet: Dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #
    def evaluate_packet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous evaluation (tests, scripts, CLIs)."""
        packet = validate_packet_wire(payload)
        report = self.engine.run_venture_sync(
            f"opp-{packet['id']}", packet_to_engine_payload(packet)
        )
        return self._finalize(packet, report)

    async def evaluate_packet_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Async evaluation for use inside a running event loop (FastAPI)."""
        packet = validate_packet_wire(payload)
        report = await self.engine.run_venture(
            f"opp-{packet['id']}", packet_to_engine_payload(packet)
        )
        return self._finalize(packet, report)

    def _finalize(self, packet: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
        assessment = self._to_assessment(packet, report)
        validate_assessment_wire(assessment)

        self._assessments[assessment["id"]] = assessment
        self._by_packet[packet["id"]] = assessment["id"]
        logger.info(
            "venture_assessment packet=%s go_no_go=%s score=%s risk=%s",
            packet["id"], assessment["go_no_go"],
            assessment["opportunity_score"], assessment["risk_level"],
        )
        return assessment

    def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        found = self._assessments.get(assessment_id)
        if found is None:
            # Callers often only hold the packet id; resolve that too.
            mapped = self._by_packet.get(assessment_id)
            found = self._assessments.get(mapped) if mapped else None
        return found

    # ------------------------------------------------------------------ #
    # Mapping
    # ------------------------------------------------------------------ #
    def _to_assessment(self, packet: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
        venture = report["venture"]
        score = float(venture["opportunity"]["opportunity_score"])
        alignment = float(venture["market"]["market_alignment"])
        roi = float(venture["financial"]["expected_roi"])
        pricing = float(venture["business_model"]["pricing"])
        risk_level = _map_risk(venture["risk"].get("risk_level", "Moderate"))
        legal_hold = venture["legal"].get("readiness") != "go"

        legal_flags = sorted(LEGAL_RISK_FLAGS & set(packet["risk_flags"]))
        finance = FINANCE_EDUCATION_FLAG in packet["risk_flags"]

        # The committee argues with itself before any verdict is written.
        cases = build_cases(packet, score, alignment)
        severe = severe_unresolved(cases)

        reasons = []
        if legal_flags:
            go_no_go, risk_level = "kill", "high"
            reasons.append(f"legal risk flags present: {legal_flags}; escalate to the operator")
        elif not packet["evidence"]:
            go_no_go = "needs_more_evidence"
            reasons.append("no evidence attached to the packet")
        elif legal_hold:
            go_no_go = "defer"
            reasons.append("legal counsel readiness is on hold")
        else:
            go_no_go = venture["go_no_go"]
            threshold = _URGENCY_MIN_SCORE[packet["urgency"]]
            comparison = "meets" if score >= threshold else "is below"
            reasons.append(f"opportunity score {score} {comparison} the {threshold} threshold")
            reasons.append(f"engine risk level: {venture['risk'].get('risk_level', 'Moderate')}")
        if severe and go_no_go == "go":
            # A high score may not erase a severe unresolved risk.
            go_no_go = "needs_more_evidence"
            reasons.append(
                f"severe unresolved adversarial case(s) cap the verdict: {severe}"
            )
        for case in cases:
            if case["stance"] == "against" and case["severity"] != "low":
                reasons.append(f"[{case['case']}] {case['argument']}")
        if finance:
            reasons.append("finance content must remain educational; no personalized advice")

        validation_plan = [step for step in [
            packet["smallest_validation_action"],
            "Draft landing-page copy and collect waitlist interest (no payment yet)",
            "Run 3-5 buyer interviews from engaged repliers",
        ] if step]

        legal_readiness = "review_required" if (legal_flags or finance or legal_hold) else "standard"

        return {
            "id": str(uuid4()),
            "opportunity_packet_id": packet["id"],
            "go_no_go": go_no_go,
            "opportunity_score": round(min(max(score, 0.0), 1.0), 3),
            "market_alignment": round(min(max(alignment, 0.0), 1.0), 3),
            "expected_roi": (
                f"modeled {roi}x over 18 months; unknown until validation — no revenue promises"
            ),
            "risk_level": risk_level,
            "legal_readiness": legal_readiness,
            "product_hypothesis": packet["possible_offer"] or packet["core_thesis"] or "unspecified",
            "pricing_hypothesis": (
                f"${pricing:.2f} modeled price point; test willingness to pay before building"
            ),
            "validation_plan": validation_plan,
            "monetization_paths": packet["monetization_paths"],
            "recommended_next_action": (
                validation_plan[0] if validation_plan else "gather evidence"
            ),
            "requires_human_approval": True,  # non-negotiable
            "reasons": reasons,
            "cases": cases,  # competing arguments, disagreement preserved
            "created_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": SCHEMA_VERSION,
        }


def _map_risk(engine_level: str) -> str:
    if engine_level in ("Ultra Low", "Low"):
        return "low"
    if engine_level == "Moderate":
        return "medium"
    return "high"


_SHARED_SERVICE: Optional[OpportunityIntakeService] = None


def get_intake_service() -> OpportunityIntakeService:
    global _SHARED_SERVICE
    if _SHARED_SERVICE is None:
        _SHARED_SERVICE = OpportunityIntakeService()
    return _SHARED_SERVICE


def set_intake_service(service: Optional[OpportunityIntakeService]) -> None:
    global _SHARED_SERVICE
    _SHARED_SERVICE = service


__all__ = [
    "OpportunityIntakeService",
    "packet_to_engine_payload",
    "get_intake_service",
    "set_intake_service",
]
