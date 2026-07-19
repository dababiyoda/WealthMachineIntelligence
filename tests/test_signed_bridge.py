"""Zero-trust bridge transport: signatures, replay, idempotency, downgrade
rejection — and the rule that a valid signature proves authenticity only,
never authorization."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from src.services.bridge_security import (
    H_IDEMPOTENCY, H_IDENTITY, H_NONCE, H_SCHEMA, H_SIGNATURE, H_TIMESTAMP,
    sign,
)
from src.services.opportunity_intake import OpportunityIntakeService, set_intake_service
from src.services.venture_protocol import SCHEMA_VERSION
from tests.test_opportunity_intake import fire_packet

KEY = "test-signing-key"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("WEALTHMACHINE_INTAKE_TOKEN", raising=False)
    monkeypatch.setenv("WEALTHMACHINE_SIGNING_KEY", KEY)
    set_intake_service(OpportunityIntakeService())
    from src.api.main import app
    yield TestClient(app)
    set_intake_service(None)


def _signed_headers(body: bytes, *, identity="daleobanks", timestamp=None,
                    nonce=None, idempotency="idem-1", schema=SCHEMA_VERSION,
                    key=KEY, signature=None):
    timestamp = timestamp or str(int(time.time()))
    nonce = nonce or f"nonce-{time.time_ns()}"
    return {
        H_IDENTITY: identity,
        H_TIMESTAMP: timestamp,
        H_NONCE: nonce,
        H_IDEMPOTENCY: idempotency,
        H_SCHEMA: schema,
        H_SIGNATURE: signature if signature is not None else sign(
            key, identity, timestamp, nonce, idempotency, schema, body
        ),
    }


def _body(packet_id="sb-1", **overrides):
    return json.dumps(fire_packet(id=packet_id, **overrides)).encode()


def test_valid_signed_request_succeeds_and_response_is_signed(client):
    body = _body("sb-valid")
    response = client.post("/api/opportunities/intake", content=body,
                           headers=_signed_headers(body, idempotency="idem-valid"))
    assert response.status_code == 200
    assert response.headers[H_IDENTITY] == "wealthmachine"
    assert response.headers.get(H_SIGNATURE)  # responses are signed too
    # Authenticity is not authorization.
    assert response.json()["requires_human_approval"] is True


def test_invalid_signature_fails_closed(client):
    body = _body("sb-badsig")
    headers = _signed_headers(body, signature="0" * 64)
    assert client.post("/api/opportunities/intake", content=body,
                       headers=headers).status_code == 401


def test_unknown_service_identity_fails_closed(client):
    body = _body("sb-unknown")
    headers = _signed_headers(body, identity="mallory")
    assert client.post("/api/opportunities/intake", content=body,
                       headers=headers).status_code == 401


def test_expired_timestamp_fails_closed(client):
    body = _body("sb-stale")
    stale = str(int(time.time()) - 3600)
    headers = _signed_headers(body, timestamp=stale)
    assert client.post("/api/opportunities/intake", content=body,
                       headers=headers).status_code == 401


def test_reused_nonce_is_replay_rejected(client):
    body = _body("sb-replay")
    headers = _signed_headers(body, nonce="nonce-fixed", idempotency="idem-r1")
    assert client.post("/api/opportunities/intake", content=body,
                       headers=headers).status_code == 200
    # Byte-identical replay: same nonce, same signature — refused.
    assert client.post("/api/opportunities/intake", content=body,
                       headers=headers).status_code == 401


def test_duplicate_idempotency_key_returns_same_assessment(client):
    body = _body("sb-idem")
    first = client.post("/api/opportunities/intake", content=body,
                        headers=_signed_headers(body, idempotency="idem-dup"))
    second = client.post("/api/opportunities/intake", content=body,
                         headers=_signed_headers(body, idempotency="idem-dup"))
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]  # engine ran once


def test_schema_downgrade_is_rejected(client):
    body = _body("sb-downgrade")
    headers = _signed_headers(body, schema="0.9")
    assert client.post("/api/opportunities/intake", content=body,
                       headers=headers).status_code == 401


def test_unsigned_request_rejected_when_key_configured(client):
    body = _body("sb-unsigned")
    assert client.post("/api/opportunities/intake", content=body,
                       headers={"Content-Type": "application/json"}).status_code == 401


def test_unsigned_allowed_in_local_mode(monkeypatch):
    monkeypatch.delenv("WEALTHMACHINE_SIGNING_KEY", raising=False)
    monkeypatch.delenv("WEALTHMACHINE_INTAKE_TOKEN", raising=False)
    set_intake_service(OpportunityIntakeService())
    from src.api.main import app
    client = TestClient(app)
    response = client.post("/api/opportunities/intake", json=fire_packet(id="sb-local"))
    assert response.status_code == 200
    set_intake_service(None)


def test_malformed_body_is_422_not_500(client):
    body = b"not json at all"
    headers = _signed_headers(body)
    assert client.post("/api/opportunities/intake", content=body,
                       headers=headers).status_code == 422
