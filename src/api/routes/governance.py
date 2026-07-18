"""Authenticated AG1/AG2 candidate control and evidence APIs.

These endpoints record and authorize work; they do not execute external tools,
publish content, move money, or sign anything.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.auth import (
    require_any_permission,
    require_permissions,
)
from src.database.connection import session_dependency
from src.governance.schemas import (
    ActionCreate,
    ApprovalCreate,
    BudgetCreate,
    CapabilityGrantCreate,
    ClaimCreate,
    ContractCreate,
    EvidenceCreate,
    EvidenceVerify,
    ExecutionCreate,
    IdentityCreate,
    KillSwitchCreate,
    KillSwitchRelease,
    VerificationCreate,
)
from src.governance.service import GovernanceService


router = APIRouter()


def get_service(session: Session = Depends(session_dependency)) -> GovernanceService:
    return GovernanceService(session)


def record_view(record: Any) -> dict[str, Any]:
    return {column.key: getattr(record, column.key) for column in record.__table__.columns}


@router.get("/status")
def governance_status(
    _user: dict[str, Any] = Depends(require_permissions("read")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return service.status()


@router.post("/identities", status_code=201)
def create_identity(
    body: IdentityCreate,
    user: dict[str, Any] = Depends(require_permissions("governance:admin")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return record_view(service.register_identity(body.model_dump(), user["user_id"]))


@router.post("/contracts", status_code=201)
def create_contract(
    body: ContractCreate,
    user: dict[str, Any] = Depends(require_permissions("governance:admin")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return record_view(service.register_contract(body.model_dump(), user["user_id"]))


@router.post("/capability-grants", status_code=201)
def create_capability_grant(
    body: CapabilityGrantCreate,
    user: dict[str, Any] = Depends(require_permissions("governance:admin")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    payload = body.model_dump()
    payload["granted_by"] = user["user_id"]
    return record_view(service.grant_capability(payload, user["user_id"]))


@router.post("/budgets", status_code=201)
def create_or_update_budget(
    body: BudgetCreate,
    user: dict[str, Any] = Depends(require_permissions("governance:admin")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return record_view(service.set_budget(body.model_dump(), user["user_id"]))


@router.post("/claims", status_code=201)
def create_claim(
    body: ClaimCreate,
    user: dict[str, Any] = Depends(require_any_permission("write", "write:evidence")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    payload = body.model_dump()
    if payload["owner_id"] != user["user_id"]:
        payload["owner_id"] = user["user_id"]
    return record_view(service.create_claim(payload, user["user_id"]))


@router.post("/evidence", status_code=201)
def create_evidence(
    body: EvidenceCreate,
    user: dict[str, Any] = Depends(require_any_permission("write", "write:evidence")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload["recorded_by"] = user["user_id"]
    return record_view(service.record_evidence(payload, user["user_id"]))


@router.post("/evidence/{evidence_id}/verification")
def verify_evidence(
    evidence_id: str,
    body: EvidenceVerify,
    user: dict[str, Any] = Depends(require_any_permission("verify", "governance:admin")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return record_view(
        service.verify_evidence(evidence_id, user["user_id"], body.status, body.reason)
    )


@router.post("/actions", status_code=201)
def create_action(
    body: ActionCreate,
    user: dict[str, Any] = Depends(require_permissions("write")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    payload = body.model_dump()
    payload["requester_id"] = user["user_id"]
    action = service.create_action(payload, user["user_id"])
    return service.reconstruct_action(action.action_id)


@router.get("/actions/{action_id}/reconstruction")
def reconstruct_action(
    action_id: str,
    _user: dict[str, Any] = Depends(require_permissions("read")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return service.reconstruct_action(action_id)


@router.post("/actions/{action_id}/approvals", status_code=201)
def approve_action(
    action_id: str,
    body: ApprovalCreate,
    user: dict[str, Any] = Depends(require_permissions("approve")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload["action_id"] = action_id
    payload["approver_id"] = user["user_id"]
    service.record_approval(payload, user["user_id"])
    return service.reconstruct_action(action_id)


@router.post("/actions/{action_id}/executions", status_code=201)
def record_execution(
    action_id: str,
    body: ExecutionCreate,
    user: dict[str, Any] = Depends(require_permissions("write")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    payload = body.model_dump()
    payload["action_id"] = action_id
    payload["executor_id"] = user["user_id"]
    service.record_execution(payload, user["user_id"])
    return service.reconstruct_action(action_id)


@router.post("/actions/{action_id}/verification", status_code=201)
def record_outcome_verification(
    action_id: str,
    body: VerificationCreate,
    user: dict[str, Any] = Depends(require_permissions("verify")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    payload = body.model_dump()
    payload["action_id"] = action_id
    payload["verifier_id"] = user["user_id"]
    service.record_verification(payload, user["user_id"])
    return service.reconstruct_action(action_id)


@router.post("/kill-switches", status_code=201)
def activate_kill_switch(
    body: KillSwitchCreate,
    user: dict[str, Any] = Depends(require_permissions("kill-switch:activate")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return record_view(service.activate_kill_switch(body.model_dump(), user["user_id"]))


@router.post("/kill-switches/{switch_id}/release")
def release_kill_switch(
    switch_id: str,
    body: KillSwitchRelease,
    user: dict[str, Any] = Depends(require_permissions("kill-switch:release")),
    service: GovernanceService = Depends(get_service),
) -> dict[str, Any]:
    return record_view(service.release_kill_switch(switch_id, user["user_id"], body.reason))
