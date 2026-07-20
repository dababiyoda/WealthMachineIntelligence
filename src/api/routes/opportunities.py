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
  with the same key.
- Idempotency: resending a request with a known idempotency key returns
  the previously computed assessment without re-running the engine.

A valid signature proves sender authenticity only. It never carries
authorization — the assessment and Foundry envelope have no execution
authority anywhere.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.services.bridge_security import (
    BridgeSecurityError,
    NonceCache,
    build_headers,
    verify_headers,
)
from src.services.foundry_adapter import (
    FoundryUnderwritingError,
    build_foundry_underwriting_envelope,
)
from src.services.opportunity_intake import get_intake_service
from src.services.venture_protocol import SCHEMA_VERSION, validate_packet_wire

router = APIRouter()

_nonce_cache = NonceCache()
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
    body = json.dumps(payload).encode()
    headers = build_headers(
        body, identity="wealthmachine", schema_version=SCHEMA_VERSION,
        idempotency_key=idempotency_key or None,
    )
    return JSONResponse(content=payload, headers=headers)


async def _verified_payload(request: Request) -> tuple[Dict[str, Any], Dict[str, str]]:
    """Token check, transport verification, and JSON parse — fail closed."""
    _check_token(request.headers.get("authorization"))
    body = await request.body()
    try:
        transport = verify_headers(dict(request.headers), body,
                                   nonce_cache=_nonce_cache)
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )
    return _signed_response(assessment)


@router.post("/ventures/{assessment_id}/foundry-envelope")
async def create_foundry_envelope(assessment_id: str, request: Request) -> JSONResponse:
    """Build a proposal-only Foundry envelope from the assessed packet.

    The request body is the separately verified commercial foundation. The
    packet and assessment are retrieved from the exact intake episode rather
    than accepted again from the caller. The result has zero execution
    authority and still requires Kernel intake, human approval, and gates.
    """
    foundation, transport = await _verified_payload(request)
    service = get_intake_service()
    assessment = service.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
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
    try:
        envelope = build_foundry_underwriting_envelope(
            packet,
            assessment,
            foundation=foundation,
        )
    except (ValueError, FoundryUnderwritingError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return _signed_response(
        envelope.to_wire(),
        transport.get("idempotency_key", ""),
    )
