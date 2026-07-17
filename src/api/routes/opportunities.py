"""OpportunityPacket intake endpoints (the DALEOBANKS bridge).

DALEOBANKS POSTs an OpportunityPacket wire payload and receives a
VentureAssessment in the response body. These endpoints only score and
recommend — nothing here launches, posts, sells, or moves money, and every
assessment carries ``requires_human_approval: true``.

Auth is local-first: when ``WEALTHMACHINE_INTAKE_TOKEN`` is set the caller
must present it as a bearer token; when unset (local/mock development) the
endpoints are open. This keeps the bridge runnable with zero credentials
while allowing a shared secret in deployment.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, status

from src.services.opportunity_intake import get_intake_service

router = APIRouter()


def _check_token(authorization: str | None) -> None:
    expected = os.getenv("WEALTHMACHINE_INTAKE_TOKEN", "")
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid intake token",
        )


async def _evaluate(payload: Dict[str, Any], authorization: str | None) -> Dict[str, Any]:
    _check_token(authorization)
    try:
        return await get_intake_service().evaluate_packet_async(payload)
    except ValueError as exc:
        # Contract violation in the inbound packet — untrusted input.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.post("/opportunities/intake")
async def intake_opportunity(
    payload: Dict[str, Any],
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    """Accept an OpportunityPacket and return its VentureAssessment."""
    return await _evaluate(payload, authorization)


@router.post("/ventures/evaluate")
async def evaluate_venture(
    payload: Dict[str, Any],
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    """Alias for intake: evaluate an OpportunityPacket directly."""
    return await _evaluate(payload, authorization)


@router.get("/ventures/{assessment_id}/assessment")
async def get_assessment(
    assessment_id: str,
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    """Fetch a stored assessment by its id (or by opportunity packet id)."""
    _check_token(authorization)
    assessment = get_intake_service().get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )
    return assessment
