"""Regression tests for the AG0 epistemic-credibility boundary."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app as operator_app
from src.api.auth import create_access_token, get_current_user, verify_token
from src.api.main import app
from src.core.epistemic import current_capability_record
from src.services.risk_management import RiskManager


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec" / "uat" / "v1"
INTERFACE = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
CLIENT = (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_current_capability_record_is_complete_and_fail_closed() -> None:
    record = current_capability_record()

    assert record["declared_stage"] == "AG0_candidate_pending_independent_review"
    assert record["operating_mode"] == "simulation"
    assert record["runtime_enforced"] is False
    assert record["authorized_external_autonomy"] == "none"
    assert record["authority"] == "recommendation_only"
    assert record["review_required"] is True
    assert record["limitations"]
    assert record["prohibited_claims"]


def test_capability_api_publishes_the_same_truth_boundary() -> None:
    response = TestClient(app).get("/api/v1/system/capabilities")

    assert response.status_code == 200
    assert response.json() == current_capability_record()


def test_operator_api_publishes_capabilities_and_denies_anonymous_dashboard() -> None:
    client = TestClient(operator_app)

    root = client.get("/api")
    denied = client.get("/api/v1/analytics/dashboard")

    assert root.status_code == 200
    assert root.json()["capability"] == current_capability_record()
    assert denied.status_code == 401


def test_claim_inventory_is_complete_and_reviewable() -> None:
    inventory = load(SPEC / "ag0-claim-inventory.json")
    coverage = inventory["coverage"]
    required = {
        "id",
        "location",
        "claim",
        "type",
        "support",
        "contradiction",
        "disposition",
        "owner",
        "test",
    }

    assert inventory["review_status"] == "candidate_pending_independent_review"
    assert coverage["consequential_claim_classes_inventoried"] == len(inventory["claims"])
    assert coverage["claim_classes_with_a_compliant_disposition"] == len(inventory["claims"])
    assert coverage["credible_claim_coverage"] == 1.0
    assert all(required <= set(claim) for claim in inventory["claims"])
    assert len({claim["id"] for claim in inventory["claims"]}) == len(inventory["claims"])


def test_operator_interface_contains_no_guaranteed_outcome_claims() -> None:
    combined = INTERFACE + CLIENT

    assert "99.99%" not in combined
    assert "Success Probability" not in combined
    assert "P(failure)" not in combined
    assert "Ultra-Low Risk Mode" not in combined
    assert "no guaranteed outcome" in combined


def test_operator_interface_contains_no_unsourced_market_numbers() -> None:
    for unsupported_literal in ("$127B", "$2.3B", "340%", "+23.4%", "+18.7%"):
        assert unsupported_literal not in INTERFACE
    assert "Example Hypothesis" in INTERFACE
    assert "Market Evidence" in INTERFACE


def test_operator_interface_does_not_claim_compliance() -> None:
    assert "All Ventures Compliant" not in INTERFACE
    assert ">Compliant<" not in INTERFACE
    assert "Not Assessed" in INTERFACE
    assert "qualified review" in INTERFACE.lower()


def test_operator_interface_contains_no_fabricated_operational_metrics() -> None:
    for unsupported_literal in ("1,247", "342h", "+156 today", "47 rules active"):
        assert unsupported_literal not in INTERFACE + CLIENT
    assert "No verified events" in INTERFACE


def test_heuristic_risk_output_is_not_a_probability_or_authority() -> None:
    assessment = RiskManager()._heuristic_assessment(
        {
            "opportunity_score": 0.7,
            "execution_confidence": 0.6,
            "expected_roi": 0.2,
            "risk_buffer": 0.1,
        }
    )

    assert "failure_probability" not in assessment
    assert assessment["heuristic_risk_index"] == assessment["risk_score"]
    assert assessment["risk_semantics"] == "uncalibrated_heuristic_index_not_probability"
    assert assessment["confidence_status"] == "not_calibrated"
    assert assessment["authority"] == "recommendation_only"


def test_offline_fallback_is_explicitly_simulated() -> None:
    assert "offline simulation" in CLIENT
    assert "ventures: []" in CLIENT
    assert "agents: []" in CLIENT
    assert "failure_probability" not in CLIENT


def test_seed_records_are_explicitly_simulated() -> None:
    seed_sources = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("src/database/init_db.py", "setup_database.py")
    )

    assert "[SIMULATION FIXTURE]" in seed_sources
    assert "Unvalidated simulation placeholder" in seed_sources
    assert "accuracy=0.0" in seed_sources
    assert "success_rate=0.0" in seed_sources
    assert "failure_probability=" not in seed_sources


def test_arbitrary_token_is_rejected_and_root_jwt_stub_is_absent() -> None:
    assert not (ROOT / "jwt.py").exists()
    assert verify_token("arbitrary-unsigned-token") is None

    valid = create_access_token({"sub": "demo-456", "username": "demo"})
    verified = verify_token(valid)
    assert verified is not None
    assert verified["user_id"] == "demo-456"


def test_missing_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_user(None))

    assert error.value.status_code == 401


def test_runtime_descriptions_match_current_capability_record() -> None:
    runtime_descriptions = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("main.py", "src/api/main.py", "pyproject.toml")
    ).lower()

    assert "uat simulation api" in runtime_descriptions
    assert "production-ready" not in runtime_descriptions
    assert "enterprise-grade ai-driven" not in runtime_descriptions


def test_legacy_documents_cannot_be_mistaken_for_current_assurance() -> None:
    deployment = (ROOT / "DEPLOYMENT_SUMMARY.md").read_text(encoding="utf-8")
    analysis = (ROOT / "WEALTHMACHINE_ANALYSIS.md").read_text(encoding="utf-8")
    replit = (ROOT / "replit.md").read_text(encoding="utf-8")

    assert "rejected as deployment evidence" in deployment
    assert "superseded and non-normative" in analysis
    assert "simulation and architecture skeleton" in replit


def test_current_capability_record_denies_external_authority() -> None:
    capability = load(SPEC / "current-capability.json")

    assert capability["authorized_external_autonomy"] == "none"
    assert capability["authority"] == "recommendation_only"
    assert any("No output authorizes" in limitation for limitation in capability["limitations"])
