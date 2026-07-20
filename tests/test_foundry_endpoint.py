import pytest
from fastapi.testclient import TestClient

from src.services.opportunity_intake import OpportunityIntakeService, set_intake_service


def strong_packet(**overrides):
    packet = {
        "id": "foundry-packet-1",
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
    packet.update(overrides)
    return packet


def foundation(**overrides):
    values = {
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
    values.update(overrides)
    return values


@pytest.fixture()
def service():
    instance = OpportunityIntakeService()
    set_intake_service(instance)
    yield instance
    set_intake_service(None)


@pytest.fixture()
def client(service, monkeypatch):
    monkeypatch.delenv("WEALTHMACHINE_INTAKE_TOKEN", raising=False)
    monkeypatch.delenv("WEALTHMACHINE_SIGNING_KEY", raising=False)
    from src.api.main import app
    return TestClient(app)


def test_assessed_packet_exports_ready_foundry_envelope(client):
    assessment_response = client.post(
        "/api/opportunities/intake",
        json=strong_packet(),
    )
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    assert assessment["go_no_go"] == "go"

    response = client.post(
        f"/api/ventures/{assessment['id']}/foundry-envelope",
        json=foundation(),
    )
    assert response.status_code == 200
    envelope = response.json()
    assert envelope["ready_for_foundry"] is True
    assert envelope["execution_authority"] == "none"
    assert envelope["requires_human_approval"] is True
    assert envelope["observed_pain"] == strong_packet()["observed_pain"]
    assert envelope["packet_digest"].startswith("sha256:")
    assert envelope["assessment_digest"].startswith("sha256:")


def test_incomplete_foundation_remains_explicitly_not_ready(client):
    assessment = client.post(
        "/api/opportunities/intake",
        json=strong_packet(id="foundry-packet-2"),
    ).json()
    response = client.post(
        f"/api/ventures/{assessment['id']}/foundry-envelope",
        json={},
    )
    assert response.status_code == 200
    envelope = response.json()
    assert envelope["ready_for_foundry"] is False
    assert "buyer" in envelope["missing_fields"]
    assert "budget_owner" in envelope["missing_fields"]
    assert envelope["execution_authority"] == "none"


def test_assessment_without_route_packet_snapshot_fails_closed(client, service):
    assessment = service.evaluate_packet(strong_packet(id="foundry-packet-direct"))
    response = client.post(
        f"/api/ventures/{assessment['id']}/foundry-envelope",
        json=foundation(),
    )
    assert response.status_code == 409
    assert "source packet is unavailable" in response.json()["detail"]


def test_foundry_endpoint_uses_same_intake_token(client, monkeypatch):
    monkeypatch.setenv("WEALTHMACHINE_INTAKE_TOKEN", "secret")
    denied = client.post(
        "/api/opportunities/intake",
        json=strong_packet(id="foundry-packet-auth"),
    )
    assert denied.status_code == 401

    assessment = client.post(
        "/api/opportunities/intake",
        json=strong_packet(id="foundry-packet-auth"),
        headers={"Authorization": "Bearer secret"},
    ).json()
    denied_envelope = client.post(
        f"/api/ventures/{assessment['id']}/foundry-envelope",
        json=foundation(),
    )
    assert denied_envelope.status_code == 401
    allowed = client.post(
        f"/api/ventures/{assessment['id']}/foundry-envelope",
        json=foundation(),
        headers={"Authorization": "Bearer secret"},
    )
    assert allowed.status_code == 200
