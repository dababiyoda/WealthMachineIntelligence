"""Signed WealthMachine -> UNIIMENTE Kernel Foundry intake client.

The client submits a ready, proposal-only underwriting envelope. The Kernel's
receipt confirms authenticated intake only. It is not a capability grant,
activation, approval, payment, or external-action authorization.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Mapping
import urllib.request

from src.services.bridge_security import (
    H_IDEMPOTENCY,
    H_IDENTITY,
    H_NONCE,
    H_SCHEMA,
    H_SIGNATURE,
    H_TIMESTAMP,
    H_TRACE,
    MAX_SKEW_SECONDS,
    NonceCache,
    build_headers,
    sign,
    signing_key,
)
from src.services.venture_protocol import SCHEMA_VERSION


class KernelFoundryClientError(ValueError):
    pass


class KernelFoundryTransportError(PermissionError):
    pass


def _canonical_sha(value: Any, field_name: str) -> str:
    text = str(value or "")
    if not text.startswith("sha256:") or len(text) != 71:
        raise KernelFoundryClientError(f"{field_name} must be a canonical sha256 reference")
    return text


def validate_kernel_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise KernelFoundryClientError("Kernel receipt must be an object")
    normalized = dict(payload)
    if normalized.get("status") != "accepted_for_foundry_analysis":
        raise KernelFoundryClientError("Kernel did not accept the opportunity for analysis")
    if normalized.get("requires_human_approval") is not True:
        raise KernelFoundryClientError("Kernel receipt must retain human approval")
    if normalized.get("execution_authority") != "none":
        raise KernelFoundryClientError("Kernel intake receipt must carry zero execution authority")
    if not str(normalized.get("opportunity_id") or "").strip():
        raise KernelFoundryClientError("Kernel receipt is missing opportunity_id")
    _canonical_sha(normalized.get("opportunity_digest"), "opportunity_digest")
    if not isinstance(normalized.get("duplicate"), bool):
        raise KernelFoundryClientError("Kernel receipt duplicate flag must be boolean")
    return normalized


class KernelFoundryClient:
    FAILURE_THRESHOLD = 3
    COOLDOWN_SECONDS = 300

    def __init__(self) -> None:
        self._response_nonces = NonceCache()
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    @property
    def url(self) -> str:
        return os.getenv("UNIIMENTE_KERNEL_URL", "").rstrip("/")

    def submit(self, envelope: Mapping[str, Any]) -> dict[str, Any]:
        if time.time() < self._circuit_open_until:
            raise ConnectionError("Kernel Foundry bridge circuit is open")
        if not self.url:
            raise KernelFoundryClientError("UNIIMENTE_KERNEL_URL is required")
        key = signing_key()
        if not key:
            raise KernelFoundryClientError(
                "WEALTHMACHINE_SIGNING_KEY is required for Kernel Foundry submission"
            )
        body_payload = dict(envelope)
        if body_payload.get("ready_for_foundry") is not True:
            raise KernelFoundryClientError("only a ready underwriting envelope may be submitted")
        if body_payload.get("execution_authority") != "none":
            raise KernelFoundryClientError("underwriting envelope must carry zero execution authority")
        packet_id = str(body_payload.get("opportunity_packet_id") or "").strip()
        assessment_digest = _canonical_sha(
            body_payload.get("assessment_digest"), "assessment_digest"
        )
        if not packet_id:
            raise KernelFoundryClientError("opportunity_packet_id is required")

        body = json.dumps(body_payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        idempotency_key = f"kernel-foundry:{packet_id}:{assessment_digest[-16:]}"
        headers = {"Content-Type": "application/json"}
        headers.update(build_headers(
            body,
            identity="wealthmachine",
            schema_version=SCHEMA_VERSION,
            idempotency_key=idempotency_key,
            trace_id=packet_id,
        ))
        request = urllib.request.Request(
            f"{self.url}/foundry/underwriting/intake",
            data=body,
            headers=headers,
            method="POST",
        )
        timeout = float(os.getenv("UNIIMENTE_KERNEL_TIMEOUT", "20"))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                response_headers = dict(response.headers.items())
            self._verify_kernel_response(response_headers, raw, key)
            receipt = validate_kernel_receipt(json.loads(raw))
        except (OSError, ValueError, json.JSONDecodeError, KernelFoundryTransportError):
            self._record_failure()
            raise

        self._consecutive_failures = 0
        return receipt

    def _verify_kernel_response(
        self,
        headers: Mapping[str, str],
        body: bytes,
        key: str,
    ) -> None:
        normalized = {str(name).lower(): str(value) for name, value in headers.items()}

        def get(name: str) -> str:
            return normalized.get(name.lower(), "")

        identity = get(H_IDENTITY)
        if identity != "uniimente-kernel":
            raise KernelFoundryTransportError("unexpected Kernel response identity")
        timestamp = get(H_TIMESTAMP)
        try:
            skew = abs(time.time() - int(timestamp))
        except (TypeError, ValueError) as exc:
            raise KernelFoundryTransportError("missing or malformed response timestamp") from exc
        if skew > MAX_SKEW_SECONDS:
            raise KernelFoundryTransportError("Kernel response timestamp outside accepted window")
        nonce = get(H_NONCE)
        if not nonce or not self._response_nonces.check_and_store(nonce):
            raise KernelFoundryTransportError("Kernel response nonce replay rejected")
        idempotency = get(H_IDEMPOTENCY)
        schema_version = get(H_SCHEMA)
        signature = get(H_SIGNATURE)
        expected = sign(
            key,
            identity,
            timestamp,
            nonce,
            idempotency,
            schema_version,
            body,
        )
        if not signature or not hmac.compare_digest(signature, expected):
            raise KernelFoundryTransportError("Kernel response signature verification failed")

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.FAILURE_THRESHOLD:
            self._circuit_open_until = time.time() + self.COOLDOWN_SECONDS


__all__ = [
    "KernelFoundryClient",
    "KernelFoundryClientError",
    "KernelFoundryTransportError",
    "validate_kernel_receipt",
]
