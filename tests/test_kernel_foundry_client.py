import json

import pytest

from src.services.bridge_security import build_headers
from src.services.kernel_foundry_client import (
    KernelFoundryClient,
    KernelFoundryClientError,
    KernelFoundryTransportError,
)
from src.services.venture_protocol import SCHEMA_VERSION


class FakeResponse:
    def __init__(self, raw, headers):
        self._raw = raw
        self.headers = headers

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def envelope(**overrides):
    payload = {
        "schema_version": "0.1",
        "source_organ": "WealthMachineIntelligence",
        "opportunity_packet_id": "packet-1",
        "packet_digest": "sha256:" + "a" * 64,
        "assessment_id": "assessment-1",
        "assessment_digest": "sha256:" + "b" * 64,
        "observed_pain": "proof is unreliable",
        "core_thesis": "verified proof may reduce disputes",
        "go_no_go": "go",
        "opportunity_score": 0.8,
        "market_alignment": 0.7,
        "risk_level": "medium",
        "legal_readiness": "standard",
        "product_hypothesis": "proof audit",
        "pricing_hypothesis": "$500 test",
        "validation_plan": ["sell one paid diagnostic"],
        "adversarial_cases": [],
        "reasons": [],
        "evidence_refs": ["sha256:" + "c" * 64],
        "buyer": "Named Buyer LLC",
        "beneficiary": "operations team",
        "pain_owner": "VP Operations",
        "budget_owner": "CFO",
        "recurring_transaction": "approve and settle verified service",
        "trapped_value_usd": 50000,
        "accepted_artifact": "signed verification receipt",
        "external_consequence": "buyer changes settlement decision",
        "lawful_path": "paid diagnostic under reviewed agreement",
        "legal_operator": "alfonso_lopez",
        "missing_fields": [],
        "blocking_reasons": [],
        "ready_for_foundry": True,
        "requires_human_approval": True,
        "execution_authority": "none",
    }
    payload.update(overrides)
    return payload


def receipt(**overrides):
    payload = {
        "status": "accepted_for_foundry_analysis",
        "opportunity_id": "packet-1:assessment-1",
        "opportunity_digest": "sha256:" + "d" * 64,
        "duplicate": False,
        "requires_human_approval": True,
        "execution_authority": "none",
    }
    payload.update(overrides)
    return payload


def signed_response(
    payload,
    *,
    idempotency="kernel-foundry:packet-1:" + "b" * 16,
    trace_id="packet-1",
    identity="uniimente-kernel",
):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    headers = build_headers(
        raw,
        identity=identity,
        schema_version=SCHEMA_VERSION,
        idempotency_key=idempotency,
        trace_id=trace_id,
    )
    return FakeResponse(raw, headers)


def configure(monkeypatch):
    monkeypatch.setenv("UNIIMENTE_KERNEL_URL", "http://kernel.local")
    monkeypatch.setenv("WEALTHMACHINE_SIGNING_KEY", "test-signing-key")


def test_submit_sends_signed_zero_authority_envelope(monkeypatch):
    configure(monkeypatch)
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["body"] = json.loads(request.data.decode())
        seen["headers"] = {name.lower(): value for name, value in request.header_items()}
        return signed_response(receipt())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = KernelFoundryClient().submit(envelope())
    assert seen["url"] == "http://kernel.local/foundry/underwriting/intake"
    assert seen["body"]["execution_authority"] == "none"
    assert seen["headers"]["x-service-identity"] == "wealthmachine"
    assert seen["headers"]["x-idempotency-key"].startswith("kernel-foundry:packet-1:")
    assert result["execution_authority"] == "none"
    assert result["requires_human_approval"] is True


def test_not_ready_or_authority_widened_envelope_is_not_sent(monkeypatch):
    configure(monkeypatch)
    with pytest.raises(KernelFoundryClientError):
        KernelFoundryClient().submit(envelope(ready_for_foundry=False))
    with pytest.raises(KernelFoundryClientError):
        KernelFoundryClient().submit(envelope(execution_authority="launch"))


def test_kernel_response_identity_idempotency_and_trace_are_bound(monkeypatch):
    configure(monkeypatch)
    client = KernelFoundryClient()

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: signed_response(receipt(), identity="other"),
    )
    with pytest.raises(KernelFoundryTransportError):
        client.submit(envelope())

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: signed_response(receipt(), idempotency="wrong"),
    )
    with pytest.raises(KernelFoundryTransportError):
        KernelFoundryClient().submit(envelope())

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: signed_response(receipt(), trace_id="other"),
    )
    with pytest.raises(KernelFoundryTransportError):
        KernelFoundryClient().submit(envelope())


def test_response_replay_is_rejected(monkeypatch):
    configure(monkeypatch)
    response = signed_response(receipt())
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: response,
    )
    client = KernelFoundryClient()
    assert client.submit(envelope())["status"] == "accepted_for_foundry_analysis"
    with pytest.raises(KernelFoundryTransportError):
        client.submit(envelope())


def test_kernel_receipt_cannot_claim_execution_authority(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: signed_response(
            receipt(execution_authority="launch")
        ),
    )
    with pytest.raises(KernelFoundryClientError):
        KernelFoundryClient().submit(envelope())


def test_missing_url_or_signing_key_fails_closed(monkeypatch):
    monkeypatch.delenv("UNIIMENTE_KERNEL_URL", raising=False)
    monkeypatch.setenv("WEALTHMACHINE_SIGNING_KEY", "test-signing-key")
    with pytest.raises(KernelFoundryClientError):
        KernelFoundryClient().submit(envelope())

    monkeypatch.setenv("UNIIMENTE_KERNEL_URL", "http://kernel.local")
    monkeypatch.delenv("WEALTHMACHINE_SIGNING_KEY", raising=False)
    with pytest.raises(KernelFoundryClientError):
        KernelFoundryClient().submit(envelope())
