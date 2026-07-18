"""Fail-closed capability and evidence disclosures for the AG0 boundary."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_RECORD_PATH = ROOT / "spec" / "uat" / "v1" / "current-capability.json"

_SAFE_FALLBACK: dict[str, Any] = {
    "spec_version": "unknown",
    "record_version": "missing",
    "as_of": None,
    "declared_stage": "unknown_restricted",
    "operating_mode": "restricted",
    "runtime_enforced": False,
    "authorized_external_autonomy": "none",
    "authority": "recommendation_only",
    "data_status": "unknown",
    "risk_output_semantics": "unknown_not_a_probability",
    "demonstrated_capabilities": [],
    "limitations": [
        "The versioned capability record is unavailable; no capability or outcome claim may be relied upon."
    ],
    "prohibited_claims": ["all unverified capability, outcome, risk, and compliance claims"],
    "permitted_cycle_outcomes": ["protection"],
    "review_required": True,
}


def current_capability_record() -> dict[str, Any]:
    """Return the repository's versioned capability record or a safe fallback."""

    try:
        with CAPABILITY_RECORD_PATH.open(encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return deepcopy(_SAFE_FALLBACK)

    required = {
        "declared_stage",
        "operating_mode",
        "runtime_enforced",
        "authorized_external_autonomy",
        "authority",
        "data_status",
        "limitations",
        "review_required",
    }
    if not required <= set(record):
        return deepcopy(_SAFE_FALLBACK)
    return record


def evidence_disclosure(source: str) -> dict[str, Any]:
    """Describe the epistemic limits attached to an API or simulation output."""

    capability = current_capability_record()
    return {
        "operating_mode": capability["operating_mode"],
        "evidence_status": capability["data_status"],
        "source": source,
        "risk_semantics": capability["risk_output_semantics"],
        "authority": capability["authority"],
        "limitations": capability["limitations"],
    }


__all__ = ["current_capability_record", "evidence_disclosure"]
