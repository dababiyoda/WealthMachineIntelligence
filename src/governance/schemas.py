"""Strict API contracts for the governed preview control plane."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IdentityCreate(StrictModel):
    identity_id: str = Field(min_length=1, max_length=128)
    identity_type: Literal["human", "agent", "service"]
    display_name: str = Field(min_length=1, max_length=255)
    venture_id: str | None = None
    role: str = Field(min_length=1, max_length=64)
    active: bool = True
    attributes: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class ContractCreate(StrictModel):
    contract_id: str = Field(min_length=1, max_length=128)
    subject_id: str = Field(min_length=1, max_length=128)
    venture_id: str = Field(min_length=1, max_length=128)
    mission: str = Field(min_length=1)
    allowed_actions: list[str] = Field(min_length=1)
    prohibited_actions: list[str] = Field(default_factory=list)
    allowed_data_classes: list[
        Literal["public", "internal", "confidential", "restricted", "regulated"]
    ] = Field(default_factory=lambda: ["public", "internal"])
    owner_id: str = Field(min_length=1)
    version: str = "1"
    status: Literal["active", "suspended", "expired", "revoked"] = "active"
    expires_at: datetime | None = None


class CapabilityGrantCreate(StrictModel):
    grant_id: str = Field(min_length=1, max_length=128)
    subject_id: str = Field(min_length=1, max_length=128)
    venture_id: str = Field(min_length=1, max_length=128)
    action_type: str = Field(min_length=1, max_length=128)
    environments: list[
        Literal["analysis", "sandbox", "staging", "production", "external"]
    ] = Field(min_length=1)
    max_risk_class: Literal["R0", "R1", "R2", "R3", "R4"]
    money_limit_minor: int = Field(default=0, ge=0)
    active: bool = True
    expires_at: datetime | None = None


class BudgetCreate(StrictModel):
    budget_id: str = Field(min_length=1, max_length=128)
    venture_id: str = Field(min_length=1, max_length=128)
    currency: str = Field(pattern="^[A-Z]{3}$")
    limit_minor: int = Field(ge=0)
    owner_id: str = Field(min_length=1)
    status: Literal["active", "frozen", "closed"] = "active"


class ClaimCreate(StrictModel):
    claim_id: str = Field(min_length=1, max_length=128)
    venture_id: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=1)
    claim_type: Literal["verified_fact", "supported_inference", "hypothesis", "unknown"]
    status: Literal["verified", "supported", "hypothesis", "unknown", "disputed"]
    owner_id: str = Field(min_length=1)
    review_at: datetime


class EvidenceSource(StrictModel):
    locator: str = Field(min_length=1)
    publisher_or_counterparty: str = Field(min_length=1)
    retrieved_at: datetime
    authoritative_for: list[str] = Field(default_factory=list)
    terms_or_consent_ref: str | None = None


class EvidenceIntegrity(StrictModel):
    sha256: str = Field(pattern="^[A-Fa-f0-9]{64}$")
    signature_ref: str | None = None
    custody_log_ref: str = Field(min_length=1)


class EvidenceCreate(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=128)
    claim_id: str = Field(min_length=1, max_length=128)
    venture_id: str = Field(min_length=1, max_length=128)
    evidence_grade: Literal[
        "E0_assertion",
        "E1_source_supported",
        "E2_direct_observation",
        "E3_counterparty_commitment",
        "E4_paid_outcome",
        "E5_repeatable_outcome",
    ]
    evidence_type: Literal[
        "document",
        "dataset",
        "interview",
        "workflow_observation",
        "commitment",
        "payment",
        "telemetry",
        "experiment",
        "legal_review",
        "security_test",
        "operational_result",
        "other",
    ]
    source: EvidenceSource
    observed_at: datetime
    recorded_at: datetime | None = None
    recorded_by: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    content_ref: str | None = None
    summary: str | None = None
    verification_status: Literal[
        "unverified", "verified", "disputed", "superseded", "invalid"
    ] = "unverified"
    verified_by: str | None = None
    contradicts_evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    integrity: EvidenceIntegrity
    classification: Literal[
        "public", "internal", "confidential", "restricted", "regulated"
    ]
    retention_policy_id: str | None = None
    review_at: datetime
    expires_at: datetime | None = None


class EvidenceVerify(StrictModel):
    status: Literal["verified", "disputed", "invalid", "superseded"]
    reason: str = Field(min_length=1)


class ActionTarget(StrictModel):
    resource_type: str
    resource_id: str
    environment: Literal["analysis", "sandbox", "staging", "production", "external"]
    counterparty_id: str | None = None


class ResourceImpact(StrictModel):
    currency: str = Field(pattern="^[A-Z]{3}$")
    money_minor: int = Field(ge=0)
    token_estimate: int = Field(ge=0)
    compute_seconds_estimate: int = Field(ge=0)
    relationship_risk: Literal["none", "low", "medium", "high"]
    data_classifications: list[
        Literal["public", "internal", "confidential", "restricted", "regulated"]
    ]


class RollbackPlan(StrictModel):
    available: bool
    plan: str
    owner_id: str
    deadline_seconds: int = Field(ge=0)


class ActionCreate(StrictModel):
    action_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=255)
    requester_id: str = Field(min_length=1)
    agent_contract_id: str = Field(min_length=1)
    venture_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    target: ActionTarget
    risk_class: Literal["R0", "R1", "R2", "R3", "R4"]
    purpose: str = Field(min_length=1)
    active_bottleneck_id: str | None = None
    evidence_refs: list[str] = Field(min_length=1)
    expected_preconditions: list[str] = Field(min_length=1)
    expected_postconditions: list[str] = Field(min_length=1)
    resource_impact: ResourceImpact
    rollback_or_compensation: RollbackPlan
    requested_at: datetime
    expires_at: datetime


class ApprovalCreate(StrictModel):
    approval_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    authority: Literal[
        "venture_sponsor",
        "designated_human",
        "legal_authority",
        "financial_authority",
        "security_authority",
        "privacy_authority",
        "human_resources_authority",
        "system_governor",
    ]
    decision: Literal["approve", "deny"]
    reason: str = Field(min_length=1)
    expires_at: datetime | None = None


class ExecutionCreate(StrictModel):
    execution_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    executor_id: str = Field(min_length=1)
    external_ref: str = Field(min_length=1)
    result: dict[str, Any]
    status: Literal["completed", "failed", "partial", "compensated"]
    executed_at: datetime


class VerificationCreate(StrictModel):
    verification_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    verifier_id: str = Field(min_length=1)
    status: Literal["verified", "failed", "disputed"]
    postconditions: dict[str, bool]
    evidence_refs: list[str] = Field(min_length=1)
    verified_at: datetime


class KillSwitchCreate(StrictModel):
    switch_id: str = Field(min_length=1)
    scope_type: Literal["portfolio", "venture", "identity", "action_type"]
    scope_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class KillSwitchRelease(StrictModel):
    reason: str = Field(min_length=1)
