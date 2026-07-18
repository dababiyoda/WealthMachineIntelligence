"""Authenticated human administration for Venture Cell capability control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from src.control import (
    ApprovalRecord,
    AuthorizationError,
    AutonomyStage,
    CapabilityGrant,
    CellStatus,
    Incident,
    IncidentSeverity,
    PolicyConfigurationError,
    StateIntegrityError,
    VentureCellCharter,
)
from src.control.models import utc_now
from src.logging_config import logger

from ..auth import get_current_user
from ..control_runtime import (
    ControlPlaneRuntime,
    ControlRuntimeConfigurationError,
    get_control_plane_runtime,
)


router = APIRouter()
IDENTIFIER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"


class CellCreateRequest(BaseModel):
    cell_id: str = Field(pattern=IDENTIFIER_PATTERN)
    mission: str = Field(min_length=3, max_length=1000)
    owner_id: str = Field(pattern=IDENTIFIER_PATTERN)
    allowed_geographies: set[str] = Field(default_factory=set)
    allowed_data_classes: set[str] = Field(default_factory=set)
    prohibited_actions: set[str] = Field(default_factory=set)
    max_daily_spend_usd: Decimal = Field(default=Decimal("0"), ge=0)
    max_total_spend_usd: Decimal = Field(default=Decimal("0"), ge=0)
    kill_conditions: list[str] = Field(default_factory=list, max_length=50)


class CellView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cell_id: str
    mission: str
    owner_id: str
    allowed_geographies: frozenset[str]
    allowed_data_classes: frozenset[str]
    prohibited_actions: frozenset[str]
    max_daily_spend_usd: Decimal
    max_total_spend_usd: Decimal
    kill_conditions: tuple[str, ...]
    policy_version: str
    status: CellStatus
    created_at: datetime


class GrantCreateRequest(BaseModel):
    grant_id: str = Field(pattern=IDENTIFIER_PATTERN)
    cell_id: str = Field(pattern=IDENTIFIER_PATTERN)
    agent_id: str = Field(pattern=IDENTIFIER_PATTERN)
    action_type: str = Field(pattern=IDENTIFIER_PATTERN)
    initial_stage: Literal["simulate", "shadow"] = "shadow"
    resource_prefixes: list[str] = Field(min_length=1, max_length=25)
    expires_at: datetime
    context_fingerprint: str = Field(min_length=3, max_length=1000)
    allowed_geographies: set[str] = Field(default_factory=set)
    allowed_data_classes: set[str] = Field(default_factory=set)
    parameter_constraints: dict[str, list[Any]] = Field(default_factory=dict)
    max_per_action_usd: Decimal = Field(default=Decimal("0"), ge=0)
    max_daily_spend_usd: Decimal = Field(default=Decimal("0"), ge=0)
    max_total_spend_usd: Decimal = Field(default=Decimal("0"), ge=0)


class GrantView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grant_id: str
    cell_id: str
    agent_id: str
    action_type: str
    stage: AutonomyStage
    resource_prefixes: tuple[str, ...]
    expires_at: datetime
    context_fingerprint: str
    allowed_geographies: frozenset[str]
    allowed_data_classes: frozenset[str]
    parameter_constraints: dict[str, tuple[Any, ...]]
    max_per_action_usd: Decimal
    max_daily_spend_usd: Decimal
    max_total_spend_usd: Decimal
    delegation_depth: int
    parent_grant_id: str | None
    created_by: str
    issued_at: datetime
    active: bool


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class ApprovalCreateRequest(BaseModel):
    approval_id: str = Field(pattern=IDENTIFIER_PATTERN)
    action_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    expires_in_minutes: int = Field(gt=0)


class ApprovalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_id: str
    action_fingerprint: str
    approver_id: str
    policy_version: str
    expires_at: datetime
    approved_at: datetime


class IncidentCreateRequest(BaseModel):
    incident_id: str = Field(pattern=IDENTIFIER_PATTERN)
    cell_id: str = Field(pattern=IDENTIFIER_PATTERN)
    severity: IncidentSeverity
    reason: str = Field(min_length=3, max_length=2000)
    grant_id: str | None = Field(default=None, pattern=IDENTIFIER_PATTERN)


class IncidentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    cell_id: str
    severity: IncidentSeverity
    reason: str
    actor_id: str
    grant_id: str | None
    occurred_at: datetime


class ControlStatusView(BaseModel):
    policy_version: str
    persistence_healthy: bool
    state_integrity: bool
    evidence_continuity: bool
    evidence_chain_integrity: bool
    ledger_sequence: int
    ledger_head_hash: str
    cell_count: int
    grant_count: int
    active_grant_count: int
    stage_distribution: dict[str, int]


@dataclass(frozen=True)
class ControlActor:
    actor_id: str
    principal: dict[str, Any]
    runtime: ControlPlaneRuntime


def require_control_runtime() -> ControlPlaneRuntime:
    """Resolve the runtime without leaking configuration or integrity details."""

    try:
        return get_control_plane_runtime()
    except (
        ControlRuntimeConfigurationError,
        PolicyConfigurationError,
        StateIntegrityError,
        OSError,
        ValueError,
    ) as exc:
        logger.error(
            "Constitutional control plane unavailable",
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Constitutional control plane unavailable",
        ) from exc


def _require_actor(
    principal: dict[str, Any],
    runtime: ControlPlaneRuntime,
    *,
    permission: str,
    authority: Literal["root", "human", "reporter"],
) -> ControlActor:
    actor_id = principal.get("user_id")
    permissions = principal.get("permissions", [])
    if not isinstance(actor_id, str) or not actor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verified subject required",
        )
    if permission not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{permission} permission required",
        )
    if authority != "reporter" and principal.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human administrator role required",
        )
    if authority == "root" and actor_id not in runtime.policy.root_authorities:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Configured root authority required",
        )
    if authority == "human" and actor_id not in runtime.policy.human_authorities:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Configured human authority required",
        )
    return ControlActor(actor_id=actor_id, principal=principal, runtime=runtime)


def require_control_reader(
    principal: dict[str, Any] = Depends(get_current_user),
    runtime: ControlPlaneRuntime = Depends(require_control_runtime),
) -> ControlActor:
    return _require_actor(
        principal,
        runtime,
        permission="control:read",
        authority="human",
    )


def require_control_root(
    principal: dict[str, Any] = Depends(get_current_user),
    runtime: ControlPlaneRuntime = Depends(require_control_runtime),
) -> ControlActor:
    return _require_actor(
        principal,
        runtime,
        permission="control:root",
        authority="root",
    )


def require_control_human(
    principal: dict[str, Any] = Depends(get_current_user),
    runtime: ControlPlaneRuntime = Depends(require_control_runtime),
) -> ControlActor:
    return _require_actor(
        principal,
        runtime,
        permission="control:approve",
        authority="human",
    )


def require_incident_reporter(
    principal: dict[str, Any] = Depends(get_current_user),
    runtime: ControlPlaneRuntime = Depends(require_control_runtime),
) -> ControlActor:
    return _require_actor(
        principal,
        runtime,
        permission="control:incident",
        authority="reporter",
    )


def _raise_policy_error(exc: Exception) -> None:
    if isinstance(exc, AuthorizationError):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, StateIntegrityError):
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        code = status.HTTP_409_CONFLICT
    raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.get("/status", response_model=ControlStatusView)
def get_control_status(
    actor: ControlActor = Depends(require_control_reader),
) -> ControlStatusView:
    runtime = actor.runtime
    grants = runtime.policy.list_grants()
    ledger_entries = runtime.evidence_ledger.entries
    stage_distribution = {stage.name: 0 for stage in AutonomyStage}
    for grant in grants:
        if grant.active:
            stage_distribution[grant.stage.name] += 1
    return ControlStatusView(
        policy_version=runtime.policy.policy_version,
        persistence_healthy=runtime.policy.persistence_healthy,
        state_integrity=runtime.state_store.verify_integrity(),
        evidence_continuity=runtime.policy.evidence_continuity,
        evidence_chain_integrity=runtime.evidence_ledger.verify_chain(),
        ledger_sequence=ledger_entries[-1].sequence if ledger_entries else 0,
        ledger_head_hash=(
            ledger_entries[-1].entry_hash if ledger_entries else "0" * 64
        ),
        cell_count=len(runtime.policy.list_cells()),
        grant_count=len(grants),
        active_grant_count=sum(grant.active for grant in grants),
        stage_distribution=stage_distribution,
    )


@router.get("/cells", response_model=list[CellView])
def list_cells(
    actor: ControlActor = Depends(require_control_reader),
) -> tuple[VentureCellCharter, ...]:
    return actor.runtime.policy.list_cells()


@router.get("/cells/{cell_id}", response_model=CellView)
def get_cell(
    cell_id: str,
    actor: ControlActor = Depends(require_control_reader),
) -> VentureCellCharter:
    cell = actor.runtime.policy.get_cell(cell_id)
    if cell is None:
        raise HTTPException(status_code=404, detail="Cell not found")
    return cell


@router.post("/cells", response_model=CellView, status_code=201)
def create_cell(
    request: CellCreateRequest,
    actor: ControlActor = Depends(require_control_root),
) -> VentureCellCharter:
    policy = actor.runtime.policy
    if request.owner_id not in policy.human_authorities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cell owner must be a configured human authority",
        )
    charter = VentureCellCharter(
        cell_id=request.cell_id,
        mission=request.mission,
        owner_id=request.owner_id,
        allowed_geographies=frozenset(request.allowed_geographies),
        allowed_data_classes=frozenset(request.allowed_data_classes),
        prohibited_actions=frozenset(request.prohibited_actions),
        max_daily_spend_usd=request.max_daily_spend_usd,
        max_total_spend_usd=request.max_total_spend_usd,
        kill_conditions=tuple(request.kill_conditions),
        policy_version=policy.policy_version,
    )
    try:
        policy.create_cell(actor.actor_id, charter)
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)
    return charter


@router.post("/cells/{cell_id}/pause", response_model=CellView)
def pause_cell(
    cell_id: str,
    request: ReasonRequest,
    actor: ControlActor = Depends(require_control_human),
) -> VentureCellCharter:
    try:
        actor.runtime.policy.pause_cell(actor.actor_id, cell_id, request.reason)
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)
    cell = actor.runtime.policy.get_cell(cell_id)
    assert cell is not None
    return cell


@router.post("/cells/{cell_id}/resume", response_model=CellView)
def resume_cell(
    cell_id: str,
    request: ReasonRequest,
    actor: ControlActor = Depends(require_control_root),
) -> VentureCellCharter:
    try:
        actor.runtime.policy.resume_cell(actor.actor_id, cell_id, request.reason)
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)
    cell = actor.runtime.policy.get_cell(cell_id)
    assert cell is not None
    return cell


@router.post("/cells/{cell_id}/terminate", response_model=CellView)
def terminate_cell(
    cell_id: str,
    request: ReasonRequest,
    actor: ControlActor = Depends(require_control_root),
) -> VentureCellCharter:
    try:
        actor.runtime.policy.terminate_cell(
            actor.actor_id,
            cell_id,
            request.reason,
        )
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)
    cell = actor.runtime.policy.get_cell(cell_id)
    assert cell is not None
    return cell


@router.get("/grants", response_model=list[GrantView])
def list_grants(
    cell_id: str | None = Query(default=None),
    actor: ControlActor = Depends(require_control_reader),
) -> tuple[CapabilityGrant, ...]:
    return actor.runtime.policy.list_grants(cell_id=cell_id)


@router.get("/grants/{grant_id}", response_model=GrantView)
def get_grant(
    grant_id: str,
    actor: ControlActor = Depends(require_control_reader),
) -> CapabilityGrant:
    grant = actor.runtime.policy.get_grant(grant_id)
    if grant is None:
        raise HTTPException(status_code=404, detail="Grant not found")
    return grant


@router.post("/grants", response_model=GrantView, status_code=201)
def create_grant(
    request: GrantCreateRequest,
    actor: ControlActor = Depends(require_control_root),
) -> CapabilityGrant:
    now = utc_now()
    if request.expires_at.tzinfo is None or request.expires_at.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Grant expiry must be timezone-aware",
        )
    latest_expiry = now + timedelta(
        hours=actor.runtime.config.max_grant_ttl_hours
    )
    if request.expires_at > latest_expiry:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Grant expiry exceeds the configured maximum TTL",
        )
    stage = (
        AutonomyStage.SIMULATE
        if request.initial_stage == "simulate"
        else AutonomyStage.SHADOW
    )
    grant = CapabilityGrant(
        grant_id=request.grant_id,
        cell_id=request.cell_id,
        agent_id=request.agent_id,
        action_type=request.action_type,
        stage=stage,
        resource_prefixes=tuple(request.resource_prefixes),
        expires_at=request.expires_at,
        context_fingerprint=request.context_fingerprint,
        allowed_geographies=frozenset(request.allowed_geographies),
        allowed_data_classes=frozenset(request.allowed_data_classes),
        parameter_constraints={
            path: tuple(values)
            for path, values in request.parameter_constraints.items()
        },
        max_per_action_usd=request.max_per_action_usd,
        max_daily_spend_usd=request.max_daily_spend_usd,
        max_total_spend_usd=request.max_total_spend_usd,
        delegation_depth=0,
    )
    try:
        return actor.runtime.policy.issue_grant(actor.actor_id, grant)
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)


@router.post("/grants/{grant_id}/revoke", response_model=GrantView)
def revoke_grant(
    grant_id: str,
    request: ReasonRequest,
    actor: ControlActor = Depends(require_control_root),
) -> CapabilityGrant:
    try:
        actor.runtime.policy.revoke_grant(
            actor.actor_id,
            grant_id,
            request.reason,
        )
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)
    grant = actor.runtime.policy.get_grant(grant_id)
    assert grant is not None
    return grant


@router.post("/approvals", response_model=ApprovalView, status_code=201)
def create_approval(
    request: ApprovalCreateRequest,
    actor: ControlActor = Depends(require_control_human),
) -> ApprovalRecord:
    if request.expires_in_minutes > actor.runtime.config.max_approval_ttl_minutes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Approval expiry exceeds the configured maximum TTL",
        )
    approval = ApprovalRecord(
        approval_id=request.approval_id,
        action_fingerprint=request.action_fingerprint,
        approver_id=actor.actor_id,
        policy_version=actor.runtime.policy.policy_version,
        expires_at=utc_now() + timedelta(minutes=request.expires_in_minutes),
    )
    try:
        actor.runtime.policy.record_approval(approval)
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)
    return approval


@router.post("/incidents", response_model=IncidentView, status_code=201)
def report_incident(
    request: IncidentCreateRequest,
    actor: ControlActor = Depends(require_incident_reporter),
) -> Incident:
    if request.grant_id:
        grant = actor.runtime.policy.get_grant(request.grant_id)
        if grant is None or grant.cell_id != request.cell_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Incident grant must exist in the referenced cell",
            )
    incident = Incident(
        incident_id=request.incident_id,
        cell_id=request.cell_id,
        severity=request.severity,
        reason=request.reason,
        actor_id=actor.actor_id,
        grant_id=request.grant_id,
    )
    try:
        actor.runtime.policy.report_incident(incident)
    except (AuthorizationError, PolicyConfigurationError, StateIntegrityError) as exc:
        _raise_policy_error(exc)
    return incident


__all__ = ["router"]
