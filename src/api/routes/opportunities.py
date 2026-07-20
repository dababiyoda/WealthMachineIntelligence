"""OpportunityPacket intake endpoints (the DALEOBANKS bridge).

DALEOBANKS POSTs an OpportunityPacket wire payload and receives a
VentureAssessment in the response body. These endpoints only score and
recommend — nothing here launches, posts, sells, or moves money, and every
assessment carries ``requires_human_approval: true``.

Transport security (zero-trust, local-first):
- With ``WEALTHMACHINE_SIGNING_KEY`` unset, transport is unsigned (mock/
  dev mode) and the optional ``WEALTHMACHINE_INTAKE_TOKEN`` bearer check
  still applies.
- With the key set, every request must carry a valid service identity,
  fresh timestamp, unused nonce, and HMAC signature; failures fail closed
  (401). Schema-version downgrades are rejected. Responses are signed
  over the exact serialized response bytes.
- Idempotency: resending a request with a known idempotency key returns
  the previously computed assessment without re-running the engine.

A valid signature proves sender authenticity only. It never carries
authorization — the assessment and Foundry envelope have no execution
authority anywhere.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.services.bridge_security import (
    BridgeSecurityError,
    NonceCache,
    build_headers,
    verify_headers,
)
from src.services.foundry_adapter import (
    FoundryUnderwritingEnvelope,
    FoundryUnderwritingError,
    build_foundry_underwriting_envelope,
)
from src.services.kernel_foundry_client import (
    KernelFoundryClient,
    KernelFoundryClientError,
    KernelFoundryTransportError,
)
from src.services.opportunity_intake import get_intake_service
from src.services.venture_protocol import SCHEMA_VERSION, validate_packet_wire

router = APIRouter()

_nonce_cache = NonceCache()
_kernel_foundry_client = KernelFoundryClient()
# The normalized packet that actually produced each assessment. This prevents
# a later Foundry request from substituting a different packet with the same id.
_packets_by_assessment: Dict[str, Dict[str, Any]] = {}
_packets_by_packet_id: Dict[str, Dict[str, Any]] = {}


def _check_token(authorization: str | None) -> None:
    expected = os.getenv("WEALTHMACHINE_INTAKE_TOKEN", "")
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid intake token",
        )


def _signed_response(payload: Dict[str, Any], idempotency_key: str = "") -> JSONResponse:
    response = JSONResponse(content=payload)
    headers = build_headers(
        response.body,
        identity="wealthmachine",
        schema_version=SCHEMA_VERSION,
        idempotency_key=idempotency_key or None,
    )
    response.headers.update(headers)
    return response


async def _verified_payload(request: Request) -> tuple[Dict[str, Any], Dict[str, str]]:
    """Token check, transport verification, and JSON parse — fail closed."""
    _check_token(request.headers.get("authorization"))
    body = await request.body()
    try:
        transport = verify_headers(
            dict(request.headers),
            body,
            nonce_cache=_nonce_cache,
        )
    except BridgeSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"body is not valid JSON: {exc}",
        )
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="body must be a JSON object",
        )
    return payload, transport


def _remember_packet(packet: Dict[str, Any], assessment: Dict[str, Any]) -> None:
    normalized = validate_packet_wire(packet)
    snapshot = dict(normalized)
    _packets_by_assessment[assessment["id"]] = snapshot
    _packets_by_packet_id[normalized["id"]] = snapshot


def _resolve_assessed_packet(assessment_id: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    service = get_intake_service()
    assessment = service.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )
    packet = (
        _packets_by_assessment.get(assessment["id"])
        or _packets_by_packet_id.get(assessment["opportunity_packet_id"])
    )
    if packet is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The normalized source packet is unavailable; re-evaluate before Foundry export",
        )
    return packet, assessment


def _build_envelope(
    assessment_id: str,
    foundation: Mapping[str, Any],
) -> FoundryUnderwritingEnvelope:
    packet, assessment = _resolve_assessed_packet(assessment_id)
    try:
        return build_foundry_underwriting_envelope(
            packet,
            assessment,
            foundation=foundation,
        )
    except (ValueError, FoundryUnderwritingError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


def _canonical_sha(value: Any, field_name: str) -> str:
    text = str(value or "")
    if not text.startswith("sha256:") or len(text) != 71:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a canonical sha256 reference",
        )
    return text


async def _evaluate(request: Request) -> JSONResponse:
    payload, transport = await _verified_payload(request)
    service = get_intake_service()

    idempotency_key = transport.get("idempotency_key", "")
    if idempotency_key:
        cached = service.get_idempotent(idempotency_key)
        if cached is not None:
            return _signed_response(cached, idempotency_key)

    try:
        assessment = await service.evaluate_packet_async(payload)
        _remember_packet(payload, assessment)
    except ValueError as exc:
        # Contract violation in the inbound packet — untrusted input.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if idempotency_key:
        service.remember_idempotent(idempotency_key, assessment)
    return _signed_response(assessment, idempotency_key)


@router.post("/opportunities/intake")
async def intake_opportunity(request: Request) -> JSONResponse:
    """Accept an OpportunityPacket and return its VentureAssessment."""
    return await _evaluate(request)


@router.post("/ventures/evaluate")
async def evaluate_venture(request: Request) -> JSONResponse:
    """Alias for intake: evaluate an OpportunityPacket directly."""
    return await _evaluate(request)


@router.get("/ventures/{assessment_id}/assessment")
async def get_assessment(assessment_id: str, request: Request) -> JSONResponse:
    """Fetch a stored assessment by its id (or by opportunity packet id)."""
    _check_token(request.headers.get("authorization"))
    assessment = get_intake_service().get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )
    return _signed_response(assessment)


@router.post("/ventures/{assessment_id}/foundry-envelope")
async def create_foundry_envelope(assessment_id: str, request: Request) -> JSONResponse:
    """Build a proposal-only Foundry envelope from the assessed packet."""
    foundation, transport = await _verified_payload(request)
    envelope = _build_envelope(assessment_id, foundation)
    return _signed_response(
        envelope.to_wire(),
        transport.get("idempotency_key", ""),
    )


@router.post("/ventures/{assessment_id}/submit-foundry")
async def submit_foundry_envelope(assessment_id: str, request: Request) -> JSONResponse:
    """Submit a ready, approval-bound envelope to the canonical Kernel.

    The caller supplies commercial foundation and a content-addressed human
    approval record. WealthMachine rebuilds the envelope from the stored packet
    and assessment, then sends it through the signed Kernel client. This does
    not grant execution authority or activate an organ.
    """
    payload, transport = await _verified_payload(request)
    foundation = payload.get("foundation")
    if not isinstance(foundation, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="foundation must be an object",
        )
    approval_hash = _canonical_sha(
        payload.get("human_approval_record_hash"),
        "human_approval_record_hash",
    )
    envelope = _build_envelope(assessment_id, foundation)
    if not envelope.ready_for_foundry:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "underwriting envelope is not ready for Kernel submission",
                "missing_fields": list(envelope.missing_fields),
                "blocking_reasons": list(envelope.blocking_reasons),
            },
        )
    wire = envelope.to_wire()
    wire["human_approval_record_hash"] = approval_hash
    try:
        kernel_receipt = _kernel_foundry_client.submit(wire)
    except KernelFoundryClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except (KernelFoundryTransportError, OSError, ConnectionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    return _signed_response(
        {
            "kernel_receipt": kernel_receipt,
            "human_approval_record_hash": approval_hash,
            "requires_human_approval": True,
            "execution_authority": "none",
        },
        transport.get("idempotency_key", ""),
    )
