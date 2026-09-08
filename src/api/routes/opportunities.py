"""Authenticated WMI adapter: exact bytes, durable claims, no external effects.

Protocol v2, Kernel boundary dependency. Synthetic localhost composition only
until live Kernel-mediated admission/routing is reviewed. A mode flag is not
authority; real founder commands and arbitrary direct-organ operation are refused.
"""
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from adapters.bridge_transport import (BridgeSecurityError, build_headers,
                                       verify_headers, body_digest)
from adapters.contract_validation import strict_json, validate_contract
from events.bridge_state import OperationConflict
from provenance.ledger import ReconciliationRequired
from src.api.auth import get_current_user
from src.services.bridge_state import get_bridge_state
from src.services.opportunity_intake import get_intake_service

router = APIRouter(dependencies=[Depends(get_current_user)])


def _scope(request):
    if (os.getenv('UNIIMENTE_BRIDGE_MODE') != 'synthetic-localhost'
            or not request.client or request.client.host not in ('127.0.0.1', '::1', 'testclient')):
        raise HTTPException(503, 'Kernel-mediated live routing not configured; direct organ bypass refused')


def _response(payload, transport, request_hash, operation='opportunity.evaluate'):
    body = json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
    headers = build_headers(body, identity='wealthmachine', schema_version=payload['schema_version'],
        idempotency_key=transport['idempotency_key'], recipient=transport['identity'],
        operation=operation, direction='response', status='200', request_digest=request_hash)
    return Response(content=body, media_type='application/json', headers=headers)


async def _admit(request, principal, operation):
    _scope(request)
    raw = await request.body()
    try:
        transport = verify_headers(dict(request.headers), raw, nonce_cache=get_bridge_state(),
            require_signature=True, expected_recipient='wealthmachine',
            expected_operation=operation, principal=principal['user_id'])
    except BridgeSecurityError as exc:
        raise HTTPException(401, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(503, str(exc)) from exc
    return raw, transport


async def _evaluate(request, principal):
    raw, transport = await _admit(request, principal, 'opportunity.evaluate')
    state = get_bridge_state()
    try:
        payload = strict_json(raw)
        validate_contract(payload, 'wire-opportunity-packet')
        if payload['schema_version'] != transport['schema_version']:
            raise ValueError('body/header contract version mismatch')
        identity, claim = state.begin(caller=principal['user_id'], operation='opportunity.evaluate',
            key=transport['idempotency_key'], body_digest=body_digest(raw))
    except OperationConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ReconciliationRequired as exc:
        raise HTTPException(409, 'reconciliation_required: persistence acknowledgment uncertain') from exc
    except OSError as exc:
        raise HTTPException(503, 'durable admission unavailable; no work invoked') from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if claim['state'] == 'completed':
        return _response(claim['result'], transport, body_digest(raw))
    if claim['state'] != 'claimed':
        raise HTTPException(409, claim['state'])
    try:
        assessment = await get_intake_service().evaluate_packet_async(payload)
        # Produce the version actually requested, not an unnegotiated upgrade.
        assessment['schema_version'] = payload['schema_version']
        validate_contract(assessment, 'wire-venture-assessment')
        state.finish(identity, assessment)
    except Exception as exc:
        state.abandon(identity)
        raise HTTPException(409, 'reconciliation_required: retained claim, no blind retry') from exc
    return _response(assessment, transport, body_digest(raw))


@router.post('/opportunities/intake')
async def intake_opportunity(request: Request, principal=Depends(get_current_user)):
    return await _evaluate(request, principal)


@router.post('/ventures/evaluate')
async def evaluate_venture(request: Request, principal=Depends(get_current_user)):
    return await _evaluate(request, principal)


@router.get('/ventures/{assessment_id}/assessment')
async def get_assessment(assessment_id: str, request: Request, principal=Depends(get_current_user)):
    operation = 'assessment.get:' + assessment_id
    raw, transport = await _admit(request, principal, operation)
    assessment = get_bridge_state().result(assessment_id, caller=principal['user_id'])
    if assessment is None:
        raise HTTPException(404, 'Assessment not found')
    return _response(assessment, transport, body_digest(raw), operation)
