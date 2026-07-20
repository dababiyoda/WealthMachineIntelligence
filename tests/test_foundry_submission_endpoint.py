import json

import pytest
from fastapi.testclient import TestClient

from src.services.bridge_security import NonceCache, build_headers, verify_headers
from src.services.kernel_foundry_client import (
    KernelFoundryClientError,
    KernelFoundryTransportError,
)
from src.services.opportunity_intake import OpportunityIntakeService, set_intake_service
from src.services.venture_protocol import SCHEMA_VERSION


APPROVAL_HASH = "sha256:" + "f" * 64


def packet(packet_id="submit-packet-1"):
    return {
        "id": packet_id,
        "source": "daleobanks",
        "source_ref": "signal-1",
        "signal_type": "product_opportunity",
        "observed_pain": "manual proof causes delayed settlement",
        "core_thesis": "verified proof may reduce disputes and delay",
        "audience": "operations leaders",
        "cultural_context": "US",
        "language": "en",
        "customer_segment": "regulated service operators",
        "buyer_type": "enterprise operator",
        "urgency": "high",
        "evidence": ["sha256:" + "a" * 64, "sha256:" + "b" * 64],
        "possible_offer": "governed workflow proof audit",
        "monetization_paths": ["paid diagnostic"],
        "risk_flags": [],
        "smallest_validation_action": "sell one paid diagnostic",
        "confidence": 0.9,
        "schema_version": "1.1",
    }


def foundation():
    return {
        "buyer": "Named Buyer LLC",
        "beneficiary": "operations team",
        "pain_owner": "VP Operations",
        "budget_owner": "CFO",
        "recurring_transaction": "approve and settle verified service",
        "trapped_value_usd": 50000,
        "accepted_artifact": "signed verification receipt",
        "external_consequence": "buyer changes settlement decision",
        "lawful_path": "paid diagnostic under reviewed agreement",
    }


def kernel_receipt():
    return {
        "status": "accepted_for_foundry_analysis",
        "opportunity_id": "submit-packet-1:assessment-1",
        "opportunity_digest": "sha256:" + "e" * 64,
        "duplicate": False,
        "requires_human_approval": True,
        "execution_authority": "none",
    }


@pytest.fixture()
def client(monkeypatch):
    set_intake_service(OpportunityIntakeService())
    monkeypatch.delenv("WEALTHMACHINE_INTAKE_TOKEN", raising=False)
    monkeypatch.delenv("WEALTHMACHINE_SIGNING_KEY", raising=False)
    from src.api.main import app
    yield TestClient(app)
    set_intake_service(None)


def assessed(client, packet_id="submit-packet-1"):
    response = client.post("/api/opportunities/intake", json=packet(packet_id))
    assert response.status_code == 200
    assessment = response.json()
    assert assessment["go_no_go"] == "go"
    return assessment


def test_submit_rebuilds_envelope_and_passes_approval_hash(client, monkeypatch):
    assessment = assessed(client)
    seen = {}

    def fake_submit(wire):
        seen["wire"] = wire
        return kernel_receipt()

    monkeypatch.setattr(
        "src.api.routes.opportunities._kernel_foundry_client.submit",
        fake_submit,
    )
    response = client.post(
        f"/api/ventures/{assessment['id']}/submit-foundry",
        json={
            "foundation": foundation(),
            "human_approval_record_hash": APPROVAL_HASH,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert seen["wire"]["ready_for_foundry"] is True
    assert seen["wire"]["human_approval_record_hash"] == APPROVAL_HASH
    assert seen["wire"]["execution_authority"] == "none"
    assert payload["kernel_receipt"]["execution_authority"] == "none"
    assert payload["human_approval_record_hash"] == APPROVAL_HASH


def test_missing_approval_or_incomplete_foundation_is_refused(client, monkeypatch):
    assessment = assessed(client, "submit-packet-2")
    called = False

    def fake_submit(wire):
        nonlocal called
        called = True
        return kernel_receipt()

    monkeypatch.setattr(
        "src.api.routes.opportunities._kernel_foundry_client.submit",
        fake_submit,
    )
    missing_approval = client.post(
        f"/api/ventures/{assessment['id']}/submit-foundry",
        json={"foundation": foundation()},
    )
    assert missing_approval.status_code == 422

    incomplete = client.post(
        f"/api/ventures/{assessment['id']}/submit-foundry",
        json={
            "foundation": {},
            "human_approval_record_hash": APPROVAL_HASH,
        },
    )
    assert incomplete.status_code == 422
    assert called is False


def test_kernel_configuration_and_transport_errors_are_separated(client, monkeypatch):
    assessment = assessed(client, "submit-packet-3")
    body = {
        "foundation": foundation(),
        "human_approval_record_hash": APPROVAL_HASH,
    }

    monkeypatch.setattr(
        "src.api.routes.opportunities._kernel_foundry_client.submit",
        lambda wire: (_ for _ in ()).throw(KernelFoundryClientError("missing url")),
    )
    unavailable = client.post(
        f"/api/ventures/{assessment['id']}/submit-foundry",
        json=body,
    )
    assert unavailable.status_code == 503

    monkeypatch.setattr(
        "src.api.routes.opportunities._kernel_foundry_client.submit",
        lambda wire: (_ for _ in ()).throw(KernelFoundryTransportError("bad receipt")),
    )
    bad_gateway = client.post(
        f"/api/ventures/{assessment['id']}/submit-foundry",
        json=body,
    )
    assert bad_gateway.status_code == 502


def test_signed_response_is_bound_to_exact_fastapi_body(client, monkeypatch):
    assessment = assessed(client, "submit-packet-4")
    monkeypatch.setattr(
        "src.api.routes.opportunities._kernel_foundry_client.submit",
        lambda wire: kernel_receipt(),
    )
    monkeypatch.setenv("WEALTHMACHINE_SIGNING_KEY", "transport-test-key")

    request_payload = {
        "foundation": foundation(),
        "human_approval_record_hash": APPROVAL_HASH,
    }
    body = json.dumps(request_payload, sort_keys=True, separators=(",", ":")).encode()
    headers = build_headers(
        body,
        identity="daleobanks",
        schema_version=SCHEMA_VERSION,
        idempotency_key="submit-signed-1",
        trace_id="submit-packet-4",
    )
    headers["Content-Type"] = "application/json"
    response = client.post(
        f"/api/ventures/{assessment['id']}/submit-foundry",
        content=body,
        headers=headers,
    )
    assert response.status_code == 200
    verified = verify_headers(
        dict(response.headers),
        response.content,
        nonce_cache=NonceCache(),
    )
    assert verified["identity"] == "wealthmachine"
    assert verified["signed"] == "true"
