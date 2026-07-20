"""WealthMachineIntelligence -> UNIIMENTE Foundry underwriting envelope.

The adapter combines a validated OpportunityPacket, VentureAssessment, and
separately verified commercial foundation. Scores and model recommendations
remain hypotheses. The output has no execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping

from src.services.venture_protocol import validate_assessment_wire, validate_packet_wire

FOUNDRY_UNDERWRITING_VERSION = "0.1"
REQUIRED_FOUNDATION_FIELDS = (
    "buyer",
    "beneficiary",
    "pain_owner",
    "budget_owner",
    "recurring_transaction",
    "accepted_artifact",
    "external_consequence",
    "lawful_path",
)


class FoundryUnderwritingError(ValueError):
    pass


@dataclass(frozen=True)
class FoundryUnderwritingEnvelope:
    schema_version: str
    source_organ: str
    opportunity_packet_id: str
    packet_digest: str
    assessment_id: str
    assessment_digest: str
    go_no_go: str
    opportunity_score: float
    market_alignment: float
    risk_level: str
    legal_readiness: str
    product_hypothesis: str
    pricing_hypothesis: str
    validation_plan: tuple[str, ...]
    adversarial_cases: tuple[dict[str, Any], ...]
    reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    buyer: str = ""
    beneficiary: str = ""
    pain_owner: str = ""
    budget_owner: str = ""
    recurring_transaction: str = ""
    trapped_value_usd: float | None = None
    accepted_artifact: str = ""
    external_consequence: str = ""
    lawful_path: str = ""
    legal_operator: str = "alfonso_lopez"
    missing_fields: tuple[str, ...] = field(default_factory=tuple)
    blocking_reasons: tuple[str, ...] = field(default_factory=tuple)
    ready_for_foundry: bool = False
    requires_human_approval: bool = True
    execution_authority: str = "none"

    def to_wire(self) -> dict[str, Any]:
        return asdict(self)


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    return "sha256:" + sha256(raw).hexdigest()


def _high_unresolved_cases(cases: list[dict[str, Any]]) -> tuple[str, ...]:
    blocked = []
    for case in cases:
        if not isinstance(case, dict):
            blocked.append("malformed_adversarial_case")
            continue
        stance = str(case.get("stance") or "")
        severity = str(case.get("severity") or "")
        resolved = bool(case.get("resolved", False))
        if stance == "against" and severity == "high" and not resolved:
            blocked.append(str(case.get("case") or "high_unresolved_case"))
    return tuple(blocked)


def build_foundry_underwriting_envelope(
    packet_payload: Mapping[str, Any],
    assessment_payload: Mapping[str, Any],
    *,
    foundation: Mapping[str, Any] | None = None,
) -> FoundryUnderwritingEnvelope:
    packet = validate_packet_wire(dict(packet_payload))
    assessment = validate_assessment_wire(dict(assessment_payload))
    if assessment["opportunity_packet_id"] != packet["id"]:
        raise FoundryUnderwritingError("assessment does not belong to the packet")

    supplied = dict(foundation or {})
    values = {name: str(supplied.get(name) or "").strip() for name in REQUIRED_FOUNDATION_FIELDS}
    missing = tuple(name for name in REQUIRED_FOUNDATION_FIELDS if not values[name])

    trapped_value = supplied.get("trapped_value_usd")
    if trapped_value is not None:
        trapped_value = float(trapped_value)
        if trapped_value < 0:
            raise FoundryUnderwritingError("trapped_value_usd cannot be negative")
    if trapped_value is None:
        missing = tuple(dict.fromkeys((*missing, "trapped_value_usd")))
    evidence_refs = tuple(str(item) for item in packet.get("evidence", ()) if str(item).strip())
    if not evidence_refs:
        missing = tuple(dict.fromkeys((*missing, "evidence_refs")))

    cases = list(assessment.get("cases") or ())
    blocks = list(_high_unresolved_cases(cases))
    verdict = assessment["go_no_go"]
    if verdict != "go":
        blocks.append(f"verdict_{verdict}")
    if assessment.get("legal_readiness") not in {"standard", "ready"}:
        blocks.append("legal_review_incomplete")
    if assessment.get("requires_human_approval") is not True:
        blocks.append("human_approval_boundary_missing")

    legal_operator = str(supplied.get("legal_operator") or "alfonso_lopez").strip()
    if legal_operator == "UNIIMENTE":
        raise FoundryUnderwritingError("UNIIMENTE is never the legal operator")

    ready = not missing and not blocks
    return FoundryUnderwritingEnvelope(
        schema_version=FOUNDRY_UNDERWRITING_VERSION,
        source_organ="WealthMachineIntelligence",
        opportunity_packet_id=packet["id"],
        packet_digest=_digest(packet),
        assessment_id=str(assessment.get("id") or ""),
        assessment_digest=_digest(assessment),
        go_no_go=verdict,
        opportunity_score=float(assessment.get("opportunity_score") or 0.0),
        market_alignment=float(assessment.get("market_alignment") or 0.0),
        risk_level=str(assessment.get("risk_level") or "unknown"),
        legal_readiness=str(assessment.get("legal_readiness") or "unreviewed"),
        product_hypothesis=str(assessment.get("product_hypothesis") or ""),
        pricing_hypothesis=str(assessment.get("pricing_hypothesis") or ""),
        validation_plan=tuple(str(item) for item in (assessment.get("validation_plan") or ())),
        adversarial_cases=tuple(cases),
        reasons=tuple(str(item) for item in (assessment.get("reasons") or ())),
        evidence_refs=evidence_refs,
        buyer=values["buyer"],
        beneficiary=values["beneficiary"],
        pain_owner=values["pain_owner"],
        budget_owner=values["budget_owner"],
        recurring_transaction=values["recurring_transaction"],
        trapped_value_usd=trapped_value,
        accepted_artifact=values["accepted_artifact"],
        external_consequence=values["external_consequence"],
        lawful_path=values["lawful_path"],
        legal_operator=legal_operator,
        missing_fields=missing,
        blocking_reasons=tuple(dict.fromkeys(blocks)),
        ready_for_foundry=ready,
    )


__all__ = [
    "FOUNDRY_UNDERWRITING_VERSION",
    "FoundryUnderwritingEnvelope",
    "FoundryUnderwritingError",
    "build_foundry_underwriting_envelope",
]
