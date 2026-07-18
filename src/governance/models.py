"""Authoritative AG1/AG2 candidate records.

These tables deliberately use ordinary SQL types.  Policy decisions are made
by deterministic code in :mod:`src.governance.service`, never by a model
prompt.  The implementation is a bounded preview candidate, not evidence that
the complete AG1 or AG2 acceptance gates have cleared.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from src.database.models import Base


class GovernanceIdentity(Base):
    __tablename__ = "governance_identities"

    identity_id = Column(String(128), primary_key=True)
    identity_type = Column(String(32), nullable=False)
    display_name = Column(String(255), nullable=False)
    venture_id = Column(String(128), nullable=True, index=True)
    role = Column(String(64), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    attributes = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class AgentContractRecord(Base):
    __tablename__ = "agent_contracts"

    contract_id = Column(String(128), primary_key=True)
    subject_id = Column(
        String(128), ForeignKey("governance_identities.identity_id"), nullable=False
    )
    venture_id = Column(String(128), nullable=False, index=True)
    mission = Column(Text, nullable=False)
    allowed_actions = Column(JSON, nullable=False, default=list)
    prohibited_actions = Column(JSON, nullable=False, default=list)
    allowed_data_classes = Column(JSON, nullable=False, default=list)
    owner_id = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False, default="1")
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("idx_contract_subject_status", "subject_id", "status"),)


class CapabilityGrantRecord(Base):
    __tablename__ = "capability_grants"

    grant_id = Column(String(128), primary_key=True)
    subject_id = Column(
        String(128), ForeignKey("governance_identities.identity_id"), nullable=False
    )
    venture_id = Column(String(128), nullable=False, index=True)
    action_type = Column(String(128), nullable=False)
    environments = Column(JSON, nullable=False, default=list)
    max_risk_class = Column(String(2), nullable=False)
    money_limit_minor = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    granted_by = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "idx_capability_subject_action",
            "subject_id",
            "venture_id",
            "action_type",
        ),
    )


class BudgetAccountRecord(Base):
    __tablename__ = "budget_accounts"

    budget_id = Column(String(128), primary_key=True)
    venture_id = Column(String(128), nullable=False, index=True)
    currency = Column(String(3), nullable=False)
    limit_minor = Column(Integer, nullable=False)
    reserved_minor = Column(Integer, nullable=False, default=0)
    spent_minor = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active")
    owner_id = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("venture_id", "currency", name="uq_budget_currency"),)


class ClaimRecord(Base):
    __tablename__ = "uat_claims"

    claim_id = Column(String(128), primary_key=True)
    venture_id = Column(String(128), nullable=False, index=True)
    statement = Column(Text, nullable=False)
    claim_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="hypothesis")
    owner_id = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    review_at = Column(DateTime(timezone=True), nullable=False)


class EvidenceRecord(Base):
    __tablename__ = "uat_evidence"

    evidence_id = Column(String(128), primary_key=True)
    claim_id = Column(String(128), ForeignKey("uat_claims.claim_id"), nullable=False)
    venture_id = Column(String(128), nullable=False, index=True)
    evidence_grade = Column(String(32), nullable=False)
    evidence_type = Column(String(32), nullable=False)
    source = Column(JSON, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recorded_by = Column(String(128), nullable=False)
    scope = Column(Text, nullable=False)
    content_ref = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    verification_status = Column(String(32), nullable=False, default="unverified")
    verified_by = Column(String(128), nullable=True)
    contradicts_evidence_ids = Column(JSON, nullable=False, default=list)
    limitations = Column(JSON, nullable=False, default=list)
    integrity_sha256 = Column(String(64), nullable=False)
    custody_log_ref = Column(String(128), nullable=False)
    classification = Column(String(32), nullable=False)
    retention_policy_id = Column(String(128), nullable=True)
    review_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_evidence_claim_status", "claim_id", "verification_status"),
        Index("idx_evidence_venture_review", "venture_id", "review_at"),
    )


class ActionRequestRecord(Base):
    __tablename__ = "uat_action_requests"

    action_id = Column(String(128), primary_key=True)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    request_hash = Column(String(64), nullable=False)
    requester_id = Column(String(128), nullable=False)
    agent_contract_id = Column(String(128), nullable=False)
    venture_id = Column(String(128), nullable=False, index=True)
    action_type = Column(String(128), nullable=False)
    target = Column(JSON, nullable=False)
    risk_class = Column(String(2), nullable=False)
    purpose = Column(Text, nullable=False)
    active_bottleneck_id = Column(String(128), nullable=True)
    evidence_refs = Column(JSON, nullable=False)
    expected_preconditions = Column(JSON, nullable=False)
    expected_postconditions = Column(JSON, nullable=False)
    resource_impact = Column(JSON, nullable=False)
    rollback_or_compensation = Column(JSON, nullable=False)
    status = Column(String(48), nullable=False, default="proposed")
    budget_reserved = Column(Boolean, nullable=False, default=False)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ApprovalRecord(Base):
    __tablename__ = "uat_approvals"

    approval_id = Column(String(128), primary_key=True)
    action_id = Column(
        String(128), ForeignKey("uat_action_requests.action_id"), nullable=False, index=True
    )
    approver_id = Column(String(128), nullable=False)
    authority = Column(String(64), nullable=False)
    decision = Column(String(16), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "action_id", "approver_id", "authority", name="uq_action_approval_authority"
        ),
    )


class PolicyDecisionRecord(Base):
    __tablename__ = "uat_policy_decisions"

    decision_id = Column(String(128), primary_key=True)
    action_id = Column(
        String(128), ForeignKey("uat_action_requests.action_id"), nullable=False, index=True
    )
    decision = Column(String(48), nullable=False)
    reasons = Column(JSON, nullable=False)
    checks = Column(JSON, nullable=False)
    evaluator = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExecutionRecord(Base):
    __tablename__ = "uat_execution_records"

    execution_id = Column(String(128), primary_key=True)
    action_id = Column(
        String(128), ForeignKey("uat_action_requests.action_id"), nullable=False, unique=True
    )
    executor_id = Column(String(128), nullable=False)
    external_ref = Column(Text, nullable=False)
    result = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VerificationRecord(Base):
    __tablename__ = "uat_verification_records"

    verification_id = Column(String(128), primary_key=True)
    action_id = Column(
        String(128), ForeignKey("uat_action_requests.action_id"), nullable=False, unique=True
    )
    verifier_id = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False)
    postconditions = Column(JSON, nullable=False)
    evidence_refs = Column(JSON, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KillSwitchRecord(Base):
    __tablename__ = "uat_kill_switches"

    switch_id = Column(String(128), primary_key=True)
    scope_type = Column(String(32), nullable=False)
    scope_id = Column(String(128), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    reason = Column(Text, nullable=False)
    activated_by = Column(String(128), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    released_by = Column(String(128), nullable=True)
    released_reason = Column(Text, nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("idx_kill_scope_active", "scope_type", "scope_id", "active"),)


class AuditEventRecord(Base):
    __tablename__ = "uat_audit_events"

    sequence = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(128), nullable=False, unique=True)
    actor_id = Column(String(128), nullable=False)
    event_type = Column(String(128), nullable=False)
    aggregate_type = Column(String(64), nullable=False)
    aggregate_id = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_audit_aggregate", "aggregate_type", "aggregate_id", "sequence"),
    )
