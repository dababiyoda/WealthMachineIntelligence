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
authorization — the assessment still has no execution authority anywhere.
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
    signing_key,
    verify_headers,
)
from src.services.opportunity_intake import get_intake_service
from src.services.venture_protocol import SCHEMA_VERSION

router = APIRouter()

_nonce_cache = NonceCache()


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
