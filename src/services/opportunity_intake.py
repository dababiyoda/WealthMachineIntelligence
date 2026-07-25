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

from src.control import (
    ActionRequest,
    AgentContract,
    ContractRegistry,
    EvidenceLedger,
    PolicyEngine,
)
from src.network_my_networth.system import NetworkWealthEngine
from src.services.venture_protocol import (
    FINANCE_EDUCATION_FLAG,
    LEGAL_RISK_FLAGS,
    SCHEMA_VERSION,
    validate_assessment_wire,
    validate_packet_wire,
)

logger = logging.getLogger(__name__)

# The intake agent's own contract. It may observe and propose (an
# assessment is a proposal); it may execute nothing, spend nothing, and
# its prohibited list names the actions this service must never grow into
# without a deliberate human decision.
INTAKE_AGENT_ID = "opportunity_intake"


def _build_intake_contract() -> AgentContract:
    return AgentContract(
        agent_id=INTAKE_AGENT_ID,
        mission="Evaluate opportunity signals and propose venture assessments "
                "for human decision",
        autonomy_level=1,
        permitted_actions=frozenset({"assess_opportunity"}),
        limits={"max_spend_usd": 0.0},
        prohibited_actions=frozenset({
            "launch_venture", "commit_capital", "publish_content",
        }),
        escalation_triggers=["capital", "launch"],
    )

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

    def __init__(
        self,
        engine: Optional[NetworkWealthEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        ledger: Optional[EvidenceLedger] = None,
    ) -> None:
        self.engine = engine or NetworkWealthEngine(
            rules=[NetworkWealthEngine.build_risk_rule()]
        )
        if policy_engine is None:
            registry = ContractRegistry()
            registry.register(_build_intake_contract())
            policy_engine = PolicyEngine(registry)
        self.policy_engine = policy_engine
        self.ledger = ledger or EvidenceLedger()
        self._assessments: Dict[str, Dict[str, Any]] = {}
        self._by_packet: Dict[str, str] = {}

    def _authorize_assessment(self, packet: Dict[str, Any]) -> None:
        """Route the act of assessing through the policy engine.

        Producing an assessment is a proposal — reversible, no spend —
        so a level-1 contract allows it. Anything else this service might
        one day be asked to do is denied or escalated here first.
        """
        decision = self.policy_engine.evaluate(ActionRequest(
            agent_id=INTAKE_AGENT_ID,
            action_type="assess_opportunity",
            description=f"assess opportunity packet {packet['id']}",
            category="propose",
            consequence="low",
            reversibility="reversible",
            venture_id=f"opp-{packet['id']}",
        ))
        if not decision.allowed:
            raise PermissionError(
                f"policy engine blocked assessment: {'; '.join(decision.reasons)}"
            )

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #
    def evaluate_packet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous evaluation (tests, scripts, CLIs)."""
        packet = validate_packet_wire(payload)
        self._authorize_assessment(packet)
        report = self.engine.run_venture_sync(
            f"opp-{packet['id']}", packet_to_engine_payload(packet)
        )
        return self._finalize(packet, report)

    async def evaluate_packet_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Async evaluation for use inside a running event loop (FastAPI)."""
        packet = validate_packet_wire(payload)
        self._authorize_assessment(packet)
        report = await self.engine.run_venture(
            f"opp-{packet['id']}", packet_to_engine_payload(packet)
        )
        return self._finalize(packet, report)

    def _finalize(self, packet: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
        assessment = self._to_assessment(packet, report)
        validate_assessment_wire(assessment)

        self._assessments[assessment["id"]] = assessment
        self._by_packet[packet["id"]] = assessment["id"]
        self._record_governance(packet, assessment)
        logger.info(
            "venture_assessment packet=%s go_no_go=%s score=%s risk=%s",
            packet["id"], assessment["go_no_go"],
            assessment["opportunity_score"], assessment["risk_level"],
        )
        return assessment

    def _record_governance(
        self, packet: Dict[str, Any], assessment: Dict[str, Any]
    ) -> None:
        """Write the assessment's evidentiary trail into the ledger.

        The packet's thesis enters the Assumption Register as an untested
        assumption; its evidence items are recorded as external evidence;
        the go/no-go itself lands as a decision that still requires human
        approval. The wire payload is unchanged — governance lives beside
        the assessment, keyed by the same venture id.
        """
        venture_id = f"opp-{packet['id']}"
        thesis = packet["core_thesis"] or packet["observed_pain"]
        assumption = self.ledger.add_assumption(
            thesis,
            venture_id=venture_id,
            criticality="high",
            source=packet["source"] or "unknown",
        )
        evidence_ids = [
            self.ledger.record_evidence(
                item,
                kind="external",
                venture_id=venture_id,
                assumption_id=assumption["id"],
                source=packet["source"] or "unknown",
                strength="weak",  # signal-stage evidence is never more than weak
            )["id"]
            for item in packet["evidence"]
        ]
        self.ledger.record_decision(
            f"assessment {assessment['go_no_go']} for packet {packet['id']}",
            venture_id=venture_id,
            actor=INTAKE_AGENT_ID,
            reasons=assessment["reasons"],
            evidence_ids=evidence_ids,
            requires_human_approval=True,
        )

    def get_governance_record(self, packet_id: str) -> Optional[Dict[str, Any]]:
        """The reconstructable trail for one packet: policy decisions,
        assumptions, and ledger events. None if the packet is unknown."""
        if packet_id not in self._by_packet:
            return None
        venture_id = f"opp-{packet_id}"
        return {
            "opportunity_packet_id": packet_id,
            "assessment_id": self._by_packet[packet_id],
            "policy_decisions": [
                d.to_dict() for d in self.policy_engine.decision_log
                if d.request.venture_id == venture_id
            ],
            "assumptions": self.ledger.assumptions_for(venture_id),
            "ledger_events": self.ledger.events_for(venture_id),
        }

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
    "INTAKE_AGENT_ID",
    "OpportunityIntakeService",
    "packet_to_engine_payload",
    "get_intake_service",
    "set_intake_service",
]
