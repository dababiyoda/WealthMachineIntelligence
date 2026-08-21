"""Issue #27 / kernel issue #5 — kernel contract consumption.

The kernel's `/contracts` are the canonical wire law. This module is the
SINGLE mapping point between that law and the DALEOBANKS transport
dialect (``venture_protocol.py``). Rules:

  - the vendored schemas under ``contracts/kernel/`` are pinned by SHA-256;
    any silent drift fails the parity test
  - kernel -> wire is documented lossy (the dialect has fewer fields)
  - wire -> kernel is enriching and FAILS CLOSED: mandatory kernel fields
    (pain_owner, budget_owner, governing_bottleneck, cheapest_decisive_test)
    must be supplied by the enrichment context, or the translation refuses
  - verdicts map to the kernel enum; ``requires_human_approval`` and
    ``execution_authority`` are constitutional constants, never mapped
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

KERNEL_SCHEMA_VERSION = "1.1"

# sha256 of the vendored kernel schemas (pinned; drift fails parity tests)
PINNED_SCHEMA_HASHES = {
    "opportunity-packet": "aaa3970164b14bb7dcca6c9dde10017f5c376c4db40f0292ad4356e0442e4c64",
    "venture-assessment": "c0ad6578fb8ded2319bb03f37c6d99c38514068c5565dbfde0ae2577219f46a7",
}

VERDICT_TO_WIRE = {"go": "go", "defer": "defer", "kill": "kill",
                   "needs_more_evidence": "needs_more_evidence"}

# kernel mandatory fields with no dialect counterpart: enrichment must supply them
KERNEL_MANDATORY_ENRICHMENT = ("pain_owner", "budget_owner", "governing_bottleneck",
                               "cheapest_decisive_test")


class ContractRefusal(ValueError):
    """Translation would lose mandatory kernel law. Fails closed."""


def _spiffe(organ: str) -> str:
    return f"spiffe://uniimente.internal/organ/{organ}"


def kernel_packet_to_wire(packet: dict) -> dict:
    """Kernel OpportunityPacket -> DALEOBANKS wire dialect (documented lossy)."""
    required = ("packet_id", "schema_version", "created_by", "observed_failure",
                "governing_bottleneck", "cheapest_decisive_test", "key_risks")
    missing = [k for k in required if k not in packet]
    if missing:
        raise ContractRefusal(f"kernel packet missing mandatory fields: {missing}")
    return {
        "id": packet["packet_id"],
        "source": packet["created_by"],
        "source_ref": "uniimente-kernel",
        "signal_type": "product_opportunity",
        "observed_pain": packet["observed_failure"],
        "core_thesis": packet.get("wedge_to_control_path", ""),
        "audience": packet.get("pain_owner", ""),
        "cultural_context": "",
        "language": "en",
        "customer_segment": packet.get("payer", packet.get("pain_owner", "")),
        "buyer_type": packet.get("mandate_capable_actor", ""),
        "urgency": "medium",
        "evidence": list(packet.get("evidence_refs", [])),
        "possible_offer": packet.get("possible_business_form") or "",
        "monetization_paths": [],
        "risk_flags": list(packet.get("key_risks", [])),
        "smallest_validation_action": packet["cheapest_decisive_test"],
        "confidence": 0.5,
        "schema_version": packet["schema_version"],
    }


def wire_packet_to_kernel(wire: dict, *, enrichment: dict) -> dict:
    """DALEOBANKS wire dialect -> kernel OpportunityPacket. Enriching, fail-closed."""
    missing = [k for k in KERNEL_MANDATORY_ENRICHMENT if not enrichment.get(k)]
    if missing:
        raise ContractRefusal(
            f"wire packet cannot become kernel law without enrichment: {missing}")
    if not wire.get("id"):
        raise ContractRefusal("wire packet missing id")
    return {
        "packet_id": wire["id"] if _is_uuid(wire["id"]) else str(uuid.uuid4()),
        "schema_version": KERNEL_SCHEMA_VERSION,
        "created_by": _spiffe("daleobanks"),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "observed_failure": wire.get("observed_pain") or wire.get("core_thesis", ""),
        "affected_actors": [wire.get("audience", "")] if wire.get("audience") else [],
        "pain_owner": enrichment["pain_owner"],
        "budget_owner": enrichment["budget_owner"],
        "payer": wire.get("customer_segment", ""),
        "mandate_capable_actor": wire.get("buyer_type", ""),
        "existing_workaround": None,
        "missing_proof": "",
        "governing_bottleneck": enrichment["governing_bottleneck"],
        "smallest_intervention": wire.get("smallest_validation_action", ""),
        "cheapest_decisive_test": enrichment["cheapest_decisive_test"],
        "possible_business_form": wire.get("possible_offer") or None,
        "capital_requirement_usd": 0.0,
        "key_risks": list(wire.get("risk_flags", [])),
        "wedge_to_control_path": wire.get("core_thesis", ""),
        "evidence_refs": [e for e in wire.get("evidence", [])
                          if isinstance(e, str) and e.startswith("sha256:")],
    }


def kernel_assessment_to_wire(assessment: dict) -> dict:
    """Kernel VentureAssessment -> wire dialect. Constitutional constants preserved."""
    for const_key, const_val in (("requires_human_approval", True),
                                 ("execution_authority", False)):
        if assessment.get(const_key) is not const_val:
            raise ContractRefusal(f"assessment violates constitution: {const_key} "
                                  f"must be {const_val}")
    verdict = assessment.get("verdict")
    if verdict not in VERDICT_TO_WIRE:
        raise ContractRefusal(f"unknown verdict {verdict!r}")
    return {
        "opportunity_packet_id": assessment["packet_id"],
        "go_no_go": VERDICT_TO_WIRE[verdict],
        "opportunity_score": assessment.get("opportunity_score"),
        "structured_reasons": list(assessment.get("structured_reasons", [])),
        "requires_human_approval": True,      # constitutional constant, never mapped
        "schema_version": assessment.get("schema_version", KERNEL_SCHEMA_VERSION),
    }


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


__all__ = ["KERNEL_SCHEMA_VERSION", "PINNED_SCHEMA_HASHES", "ContractRefusal",
           "kernel_packet_to_wire", "wire_packet_to_kernel", "kernel_assessment_to_wire"]
