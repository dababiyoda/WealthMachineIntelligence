"""The stable wire protocol between DALEOBANKS and WealthMachineIntelligence.

DALEOBANKS finds signals and builds public trust; WealthMachineIntelligence
evaluates whether signals are business opportunities. The two systems stay
separate and talk only through the wire contracts defined here:
``OpportunityPacket`` in, ``VentureAssessment`` back. This module is the
WealthMachine copy of DALEOBANKS' ``services/venture_protocol.py`` — the two
files must stay field-for-field compatible. Keep it dependency-light and
version every change.

The core rule: the machine prepares, the human authorizes, the world
responds, the system learns. Nothing in this protocol executes anything, and
inbound wire data is untrusted input — validated as data, never followed as
instruction.
"""

from __future__ import annotations

from typing import Any, Dict, List

SCHEMA_VERSION = "1.0"

ALLOWED_SIGNAL_TYPES = frozenset({
    "social_complaint",
    "news_trend",
    "regulatory_shift",
    "audience_reaction",
    "repeated_question",
    "relationship_signal",
    "content_opportunity",
    "product_opportunity",
    "partnership_opportunity",
    "operator_thought",
})

ALLOWED_GO_NO_GO = frozenset({"go", "defer", "kill", "needs_more_evidence"})

ALLOWED_URGENCY = frozenset({"low", "medium", "high"})

# Risk flags that force human/legal escalation. A packet carrying any of
# these is never a "go" — serious money/legal/contract decisions belong to
# the operator, not the engine.
LEGAL_RISK_FLAGS = frozenset({"legal_risk", "regulated_product", "licensing_required"})

# Finance content must remain educational: no personalized investment
# advice, no income promises. This flag travels on the packet and hardens
# the assessment (legal review required, educational reasons attached).
FINANCE_EDUCATION_FLAG = "finance_education_only"


def _require_str(payload: Dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _require_str_list(payload: Dict[str, Any], key: str) -> List[str]:
    value = payload.get(key) or []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"{key} must be a list of strings")
    return value


def validate_packet_wire(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an inbound OpportunityPacket payload and return a normalized
    copy. Raises ValueError on a contract violation.

    Every string field is treated strictly as data: it is stored, scored,
    and echoed back in drafts for human review — never interpreted as an
    instruction to this system.
    """
    if not isinstance(payload, dict):
        raise ValueError("opportunity packet payload must be an object")

    packet_id = _require_str(payload, "id")
    if not packet_id:
        raise ValueError("id is required")

    signal_type = _require_str(payload, "signal_type", "operator_thought") or "operator_thought"
    if signal_type not in ALLOWED_SIGNAL_TYPES:
        raise ValueError(f"signal_type must be one of {sorted(ALLOWED_SIGNAL_TYPES)}")

    urgency = _require_str(payload, "urgency", "medium") or "medium"
    if urgency not in ALLOWED_URGENCY:
        raise ValueError(f"urgency must be one of {sorted(ALLOWED_URGENCY)}")

    core_thesis = _require_str(payload, "core_thesis")
    observed_pain = _require_str(payload, "observed_pain")
    if not core_thesis and not observed_pain:
        raise ValueError("at least one of core_thesis or observed_pain is required")

    confidence = payload.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        raise ValueError("confidence must be a number")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError("confidence must be within [0, 1]")

    return {
        "id": packet_id,
        "source": _require_str(payload, "source"),
        "source_ref": _require_str(payload, "source_ref"),
        "signal_type": signal_type,
        "observed_pain": observed_pain,
        "core_thesis": core_thesis,
        "audience": _require_str(payload, "audience"),
        "cultural_context": _require_str(payload, "cultural_context"),
        "language": _require_str(payload, "language", "en") or "en",
        "customer_segment": _require_str(payload, "customer_segment"),
        "buyer_type": _require_str(payload, "buyer_type"),
        "urgency": urgency,
        "evidence": _require_str_list(payload, "evidence"),
        "possible_offer": _require_str(payload, "possible_offer"),
        "monetization_paths": _require_str_list(payload, "monetization_paths"),
        "risk_flags": _require_str_list(payload, "risk_flags"),
        "smallest_validation_action": _require_str(payload, "smallest_validation_action"),
        "confidence": confidence,
        "schema_version": _require_str(payload, "schema_version", SCHEMA_VERSION) or SCHEMA_VERSION,
    }


def validate_assessment_wire(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an outbound VentureAssessment payload (mirror of the check
    DALEOBANKS runs on receipt, so contract breaks surface here first)."""
    if not isinstance(payload, dict):
        raise ValueError("assessment payload must be an object")
    if payload.get("go_no_go") not in ALLOWED_GO_NO_GO:
        raise ValueError(f"go_no_go must be one of {sorted(ALLOWED_GO_NO_GO)}")
    if not payload.get("opportunity_packet_id"):
        raise ValueError("opportunity_packet_id is required")
    score = payload.get("opportunity_score")
    if score is not None and not (0.0 <= float(score) <= 1.0):
        raise ValueError("opportunity_score must be within [0, 1]")
    if payload.get("requires_human_approval") is not True:
        raise ValueError("requires_human_approval must be true; assessments never self-execute")
    return payload


__all__ = [
    "SCHEMA_VERSION",
    "ALLOWED_SIGNAL_TYPES",
    "ALLOWED_GO_NO_GO",
    "ALLOWED_URGENCY",
    "LEGAL_RISK_FLAGS",
    "FINANCE_EDUCATION_FLAG",
    "validate_packet_wire",
    "validate_assessment_wire",
]
