"""Adversarial and integration tests for the AG1/AG2 vertical slice."""

from __future__ import annotations

from datetime import timedelta
import hashlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.database.models import Base
from src.governance import models as governance_models  # noqa: F401
from src.governance.models import AuditEventRecord
from src.governance.service import GovernanceError, GovernanceService, utcnow


@pytest.fixture()
def service() -> GovernanceService:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    instance = GovernanceService(session)
    yield instance
    session.close()
    engine.dispose()


def register_identity(
    service: GovernanceService,
    identity_id: str,
    *,
    authorities: list[str] | None = None,
    identity_type: str = "human",
) -> None:
    service.register_identity(
        {
            "identity_id": identity_id,
            "identity_type": identity_type,
            "display_name": identity_id,
            "venture_id": "venture-a",
            "role": "test-role",
            "attributes": {"authorities": authorities or []},
            "expires_at": utcnow() + timedelta(days=1),
        },
        actor_id="bootstrap",
    )


def seed_requester(
    service: GovernanceService,
    *,
    action_type: str = "research",
    risk_class: str = "R1",
    environments: list[str] | None = None,
    money_limit_minor: int = 0,
) -> None:
    register_identity(service, "requester")
    register_identity(service, "reviewer")
    register_identity(service, "approver-one", authorities=["designated_human", "system_governor"])
    register_identity(service, "approver-two", authorities=["financial_authority"])
    service.register_contract(
        {
            "contract_id": "contract-requester",
            "subject_id": "requester",
            "venture_id": "venture-a",
            "mission": "Run one bounded test.",
            "allowed_actions": [action_type],
            "prohibited_actions": [],
            "allowed_data_classes": ["public", "internal"],
            "owner_id": "approver-one",
            "expires_at": utcnow() + timedelta(days=1),
        },
        actor_id="approver-one",
    )
    service.grant_capability(
        {
            "grant_id": "grant-requester",
            "subject_id": "requester",
            "venture_id": "venture-a",
            "action_type": action_type,
            "environments": environments or ["analysis", "sandbox"],
            "max_risk_class": risk_class,
            "money_limit_minor": money_limit_minor,
            "granted_by": "approver-one",
            "expires_at": utcnow() + timedelta(days=1),
        },
        actor_id="approver-one",
    )
    service.set_budget(
        {
            "budget_id": "budget-a",
            "venture_id": "venture-a",
            "currency": "USD",
            "limit_minor": money_limit_minor,
            "owner_id": "approver-one",
        },
        actor_id="approver-one",
    )
    service.create_claim(
        {
            "claim_id": "claim-a",
            "venture_id": "venture-a",
            "statement": "The bounded test can answer the active uncertainty.",
            "claim_type": "hypothesis",
            "status": "hypothesis",
            "owner_id": "requester",
            "review_at": utcnow() + timedelta(days=1),
        },
        actor_id="requester",
    )
    service.record_evidence(
        {
            "evidence_id": "evidence-a",
            "claim_id": "claim-a",
            "venture_id": "venture-a",
            "evidence_grade": "E1_source_supported",
            "evidence_type": "document",
            "source": {
                "locator": "urn:test:source",
                "publisher_or_counterparty": "test source",
                "retrieved_at": utcnow(),
            },
            "observed_at": utcnow(),
            "recorded_by": "requester",
            "scope": "Only the bounded test design.",
            "summary": "Fixture evidence for policy evaluation.",
            "verification_status": "unverified",
            "integrity": {
                "sha256": hashlib.sha256(b"fixture evidence").hexdigest(),
                "custody_log_ref": "audit:evidence-a",
            },
            "classification": "internal",
            "review_at": utcnow() + timedelta(days=1),
        },
        actor_id="requester",
    )


def action_payload(
    *,
    action_id: str = "action-a",
    action_type: str = "research",
    risk_class: str = "R1",
    environment: str = "sandbox",
    money_minor: int = 0,
) -> dict:
    return {
        "action_id": action_id,
        "idempotency_key": f"idempotency-{action_id}",
        "requester_id": "requester",
        "agent_contract_id": "contract-requester",
        "venture_id": "venture-a",
        "action_type": action_type,
        "target": {
            "resource_type": "test",
            "resource_id": action_id,
            "environment": environment,
            "counterparty_id": None,
        },
        "risk_class": risk_class,
        "purpose": "Resolve the active uncertainty.",
        "active_bottleneck_id": "bottleneck-a",
        "evidence_refs": ["evidence-a"],
        "expected_preconditions": ["evidence is current"],
        "expected_postconditions": ["test result is recorded"],
        "resource_impact": {
            "currency": "USD",
            "money_minor": money_minor,
            "token_estimate": 100,
            "compute_seconds_estimate": 1,
            "relationship_risk": "none",
            "data_classifications": ["internal"],
        },
        "rollback_or_compensation": {
            "available": True,
            "plan": "Discard the sandbox output.",
            "owner_id": "requester",
            "deadline_seconds": 60,
        },
        "requested_at": utcnow(),
        "expires_at": utcnow() + timedelta(hours=1),
    }


def test_valid_r1_action_is_authorized_and_reconstructable(
    service: GovernanceService,
) -> None:
    seed_requester(service)
    action = service.create_action(action_payload(), actor_id="requester")
    reconstruction = service.reconstruct_action(action.action_id)

    assert action.status == "authorized"
    assert reconstruction["policy_decisions"][-1]["decision"] == "authorized"
    assert reconstruction["evidence"][0]["evidence_id"] == "evidence-a"
    assert reconstruction["audit_chain_valid"] is True


def test_idempotency_replay_returns_original_and_conflicting_reuse_is_denied(
    service: GovernanceService,
) -> None:
    seed_requester(service)
    payload = action_payload()
    first = service.create_action(payload, actor_id="requester")
    replay = service.create_action(payload, actor_id="requester")
    assert replay.action_id == first.action_id

    changed = action_payload()
    changed["purpose"] = "A different request with the same key."
    with pytest.raises(GovernanceError, match="idempotency key"):
        service.create_action(changed, actor_id="requester")


def test_missing_capability_and_budget_fail_closed(service: GovernanceService) -> None:
    seed_requester(service)
    payload = action_payload(action_id="held-action")
    payload["action_type"] = "ungranted-action"
    action = service.create_action(payload, actor_id="requester")
    decision = service.reconstruct_action(action.action_id)["policy_decisions"][-1]

    assert action.status == "held"
    assert "missing_capability" in decision["reasons"]


def test_capability_grant_cannot_impersonate_its_grantor(
    service: GovernanceService,
) -> None:
    register_identity(service, "requester")
    with pytest.raises(GovernanceError, match="grantor"):
        service.grant_capability(
            {
                "grant_id": "spoofed-grant",
                "subject_id": "requester",
                "venture_id": "venture-a",
                "action_type": "research",
                "environments": ["analysis"],
                "max_risk_class": "R0",
                "money_limit_minor": 0,
                "granted_by": "someone-else",
                "expires_at": utcnow() + timedelta(days=1),
            },
            actor_id="approver-one",
        )


def test_requester_cannot_understate_the_minimum_risk_class(
    service: GovernanceService,
) -> None:
    seed_requester(
        service,
        action_type="transfer_funds",
        risk_class="R4",
        environments=["external"],
        money_limit_minor=2_000,
    )
    action = service.create_action(
        action_payload(
            action_type="transfer_funds",
            risk_class="R1",
            environment="external",
            money_minor=2_000,
        ),
        actor_id="requester",
    )
    decision = service.reconstruct_action(action.action_id)["policy_decisions"][-1]

    assert action.status == "held"
    assert "risk_class_understated" in decision["reasons"]
    assert decision["checks"]["risk_classification"] == {
        "passed": False,
        "declared": "R1",
        "minimum": "R4",
    }


def test_future_and_expired_action_windows_fail_closed(
    service: GovernanceService,
) -> None:
    seed_requester(service)

    future_payload = action_payload(action_id="future-action")
    future_payload["requested_at"] = utcnow() + timedelta(hours=1)
    future_payload["expires_at"] = utcnow() + timedelta(hours=2)
    future = service.create_action(future_payload, actor_id="requester")
    assert future.status == "held"
    assert "action_not_yet_valid" in service.reconstruct_action(future.action_id)[
        "policy_decisions"
    ][-1]["reasons"]

    expired_payload = action_payload(action_id="expired-action")
    expired_payload["requested_at"] = utcnow() - timedelta(hours=2)
    expired_payload["expires_at"] = utcnow() - timedelta(hours=1)
    expired = service.create_action(expired_payload, actor_id="requester")
    assert expired.status == "held"
    assert "action_expired" in service.reconstruct_action(expired.action_id)[
        "policy_decisions"
    ][-1]["reasons"]


def test_kill_switch_blocks_existing_capability_without_model_cooperation(
    service: GovernanceService,
) -> None:
    seed_requester(service)
    service.activate_kill_switch(
        {
            "switch_id": "kill-venture-a",
            "scope_type": "venture",
            "scope_id": "venture-a",
            "reason": "Adversarial containment test",
        },
        actor_id="approver-one",
    )
    action = service.create_action(
        action_payload(action_id="blocked-action"), actor_id="requester"
    )

    assert action.status == "held"
    assert "venture_or_portfolio_kill_switch_active" in service.reconstruct_action(
        action.action_id
    )["policy_decisions"][-1]["reasons"]


def test_kill_switch_is_rechecked_before_execution_is_recorded(
    service: GovernanceService,
) -> None:
    seed_requester(service)
    action = service.create_action(action_payload(), actor_id="requester")
    assert action.status == "authorized"

    service.activate_kill_switch(
        {
            "switch_id": "kill-after-authorization",
            "scope_type": "venture",
            "scope_id": "venture-a",
            "reason": "Contain an action that was already authorized.",
        },
        actor_id="approver-one",
    )
    with pytest.raises(GovernanceError, match="immediate policy re-evaluation"):
        service.record_execution(
            {
                "execution_id": "execution-blocked",
                "action_id": action.action_id,
                "executor_id": "requester",
                "external_ref": "urn:test:blocked",
                "result": {"actual_money_minor": 0},
                "status": "completed",
                "executed_at": utcnow(),
            },
            actor_id="requester",
        )

    assert action.status == "held"
    assert (
        service.session.query(governance_models.ExecutionRecord)
        .filter_by(action_id=action.action_id)
        .first()
        is None
    )


def test_r3_requires_verified_evidence_and_two_distinct_human_approvers(
    service: GovernanceService,
) -> None:
    seed_requester(
        service,
        action_type="material_spend",
        risk_class="R3",
        environments=["external"],
        money_limit_minor=5_000,
    )
    payload = action_payload(
        action_type="material_spend",
        risk_class="R3",
        environment="external",
        money_minor=5_000,
    )
    action = service.create_action(payload, actor_id="requester")
    assert action.status == "held"

    service.verify_evidence("evidence-a", "reviewer", "verified", "Source reproduced")
    service.evaluate_action(action.action_id, actor_id="policy-engine")
    assert action.status == "requires_human_approval"

    service.record_approval(
        {
            "approval_id": "approval-one",
            "action_id": action.action_id,
            "approver_id": "approver-one",
            "authority": "designated_human",
            "decision": "approve",
            "reason": "Purpose and limits verified.",
        },
        actor_id="approver-one",
    )
    assert action.status == "requires_human_approval"
    service.record_approval(
        {
            "approval_id": "approval-two",
            "action_id": action.action_id,
            "approver_id": "approver-two",
            "authority": "financial_authority",
            "decision": "approve",
            "reason": "Budget and counterparty verified.",
        },
        actor_id="approver-two",
    )

    assert action.status == "authorized"
    assert service.reconstruct_action(action.action_id)["policy_decisions"][-1][
        "checks"
    ]["approvals"]["distinct_approvers"] == 2
    budget = service.session.get(
        governance_models.BudgetAccountRecord,
        "budget-a",
    )
    assert budget.reserved_minor == 5_000
    service.evaluate_action(action.action_id, actor_id="policy-engine")
    assert budget.reserved_minor == 5_000

    with pytest.raises(GovernanceError, match="independent"):
        service.record_execution(
            {
                "execution_id": "execution-requester-denied",
                "action_id": action.action_id,
                "executor_id": "requester",
                "external_ref": "urn:test:requester-denied",
                "result": {"actual_money_minor": 4_000},
                "status": "completed",
                "executed_at": utcnow(),
            },
            actor_id="requester",
        )
    register_identity(service, "independent-executor")
    service.record_execution(
        {
            "execution_id": "execution-r3",
            "action_id": action.action_id,
            "executor_id": "independent-executor",
            "external_ref": "urn:test:r3-execution",
            "result": {"actual_money_minor": 4_000},
            "status": "completed",
            "executed_at": utcnow(),
        },
        actor_id="independent-executor",
    )
    assert budget.reserved_minor == 0
    assert budget.spent_minor == 4_000


def test_r4_is_never_authorized_for_autonomous_execution(
    service: GovernanceService,
) -> None:
    seed_requester(
        service,
        action_type="transfer_funds",
        risk_class="R4",
        environments=["external"],
        money_limit_minor=2_000,
    )
    service.verify_evidence("evidence-a", "reviewer", "verified", "Source reproduced")
    action = service.create_action(
        action_payload(
            action_type="transfer_funds",
            risk_class="R4",
            environment="external",
            money_minor=2_000,
        ),
        actor_id="requester",
    )
    for approval in (
        {
            "approval_id": "approval-one",
            "approver_id": "approver-one",
            "authority": "designated_human",
        },
        {
            "approval_id": "approval-two",
            "approver_id": "approver-two",
            "authority": "financial_authority",
        },
    ):
        service.record_approval(
            {
                **approval,
                "action_id": action.action_id,
                "decision": "approve",
                "reason": "Explicit test approval.",
            },
            actor_id=approval["approver_id"],
        )

    assert action.status == "human_execution_only"
    assert "R4_autonomous_execution_prohibited" in service.reconstruct_action(
        action.action_id
    )["policy_decisions"][-1]["reasons"]


def test_execution_and_outcome_verification_require_independent_humans(
    service: GovernanceService,
) -> None:
    seed_requester(service)
    action = service.create_action(action_payload(), actor_id="requester")
    service.record_execution(
        {
            "execution_id": "execution-a",
            "action_id": action.action_id,
            "executor_id": "requester",
            "external_ref": "urn:test:execution",
            "result": {"actual_money_minor": 0},
            "status": "completed",
            "executed_at": utcnow(),
        },
        actor_id="requester",
    )
    with pytest.raises(GovernanceError, match="independent"):
        service.record_verification(
            {
                "verification_id": "verification-bad",
                "action_id": action.action_id,
                "verifier_id": "requester",
                "status": "verified",
                "postconditions": {"test result is recorded": True},
                "evidence_refs": ["evidence-a"],
                "verified_at": utcnow(),
            },
            actor_id="requester",
        )
    with pytest.raises(GovernanceError, match="independently verified evidence"):
        service.record_verification(
            {
                "verification_id": "verification-unverified-evidence",
                "action_id": action.action_id,
                "verifier_id": "reviewer",
                "status": "verified",
                "postconditions": {"test result is recorded": True},
                "evidence_refs": ["evidence-a"],
                "verified_at": utcnow(),
            },
            actor_id="reviewer",
        )
    service.verify_evidence(
        "evidence-a",
        "approver-one",
        "verified",
        "Outcome source and integrity were reproduced.",
    )
    with pytest.raises(GovernanceError, match="every expected postcondition"):
        service.record_verification(
            {
                "verification_id": "verification-wrong-postcondition",
                "action_id": action.action_id,
                "verifier_id": "reviewer",
                "status": "verified",
                "postconditions": {"different condition": True},
                "evidence_refs": ["evidence-a"],
                "verified_at": utcnow(),
            },
            actor_id="reviewer",
        )
    service.record_verification(
        {
            "verification_id": "verification-good",
            "action_id": action.action_id,
            "verifier_id": "reviewer",
            "status": "verified",
            "postconditions": {"test result is recorded": True},
            "evidence_refs": ["evidence-a"],
            "verified_at": utcnow(),
        },
        actor_id="reviewer",
    )
    assert action.status == "verified"


def test_expired_human_cannot_approve_or_release_a_kill_switch(
    service: GovernanceService,
) -> None:
    seed_requester(
        service,
        action_type="material_spend",
        risk_class="R3",
        environments=["external"],
        money_limit_minor=5_000,
    )
    service.verify_evidence("evidence-a", "reviewer", "verified", "Source reproduced")
    action = service.create_action(
        action_payload(
            action_type="material_spend",
            risk_class="R3",
            environment="external",
            money_minor=5_000,
        ),
        actor_id="requester",
    )
    service.activate_kill_switch(
        {
            "switch_id": "human-expiry-test",
            "scope_type": "action_type",
            "scope_id": "unrelated",
            "reason": "Exercise release authority expiry.",
        },
        actor_id="approver-one",
    )
    approver = service.session.get(
        governance_models.GovernanceIdentity,
        "approver-one",
    )
    approver.expires_at = utcnow() - timedelta(seconds=1)
    service.session.flush()

    with pytest.raises(GovernanceError, match="active human"):
        service.record_approval(
            {
                "approval_id": "expired-approval",
                "action_id": action.action_id,
                "approver_id": "approver-one",
                "authority": "designated_human",
                "decision": "approve",
                "reason": "This identity is expired.",
            },
            actor_id="approver-one",
        )
    with pytest.raises(GovernanceError, match="active human"):
        service.release_kill_switch(
            "human-expiry-test",
            actor_id="approver-one",
            reason="Expired identities cannot release containment.",
        )


def test_audit_chain_detects_direct_record_tampering(service: GovernanceService) -> None:
    seed_requester(service)
    service.create_action(action_payload(), actor_id="requester")
    assert service.verify_audit_chain() is True
    event = service.session.query(AuditEventRecord).order_by(AuditEventRecord.sequence).first()
    event.payload = {"tampered": True}
    service.session.flush()
    assert service.verify_audit_chain() is False


def test_canonical_web_app_exposes_governance_and_blocks_legacy_mutations() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        status_response = client.get("/api/v1/governance/status", headers=headers)
        blocked_launch = client.post(
            "/api/v1/ventures/",
            headers=headers,
            json={"name": "Unsafe", "venture_type": "saas"},
        )
        readiness = client.get("/health/ready")

        assert status_response.status_code == 200
        assert status_response.json()["autonomous_external_authority"] == "none"
        assert status_response.json()["audit_chain_valid"] is True
        assert blocked_launch.status_code == 409
        assert readiness.status_code == 200


def test_governance_api_reconstructs_one_authorized_r0_action() -> None:
    suffix = uuid4().hex
    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        now = utcnow()
        claim_id = f"claim-{suffix}"
        evidence_id = f"evidence-{suffix}"
        action_id = f"action-{suffix}"

        claim = client.post(
            "/api/v1/governance/claims",
            headers=headers,
            json={
                "claim_id": claim_id,
                "venture_id": "preview",
                "statement": "The sandbox test can resolve one uncertainty.",
                "claim_type": "hypothesis",
                "status": "hypothesis",
                "owner_id": "admin-123",
                "review_at": (now + timedelta(days=1)).isoformat(),
            },
        )
        evidence = client.post(
            "/api/v1/governance/evidence",
            headers=headers,
            json={
                "evidence_id": evidence_id,
                "claim_id": claim_id,
                "venture_id": "preview",
                "evidence_grade": "E0_assertion",
                "evidence_type": "other",
                "source": {
                    "locator": "urn:test:api",
                    "publisher_or_counterparty": "operator",
                    "retrieved_at": now.isoformat(),
                },
                "observed_at": now.isoformat(),
                "recorded_by": "admin-123",
                "scope": "Sandbox only.",
                "verification_status": "unverified",
                "integrity": {
                    "sha256": hashlib.sha256(b"api evidence").hexdigest(),
                    "custody_log_ref": f"audit:{evidence_id}",
                },
                "classification": "internal",
                "review_at": (now + timedelta(days=1)).isoformat(),
            },
        )
        action = client.post(
            "/api/v1/governance/actions",
            headers=headers,
            json={
                "action_id": action_id,
                "idempotency_key": f"idem-{suffix}",
                "requester_id": "admin-123",
                "agent_contract_id": "preview-contract-admin-123",
                "venture_id": "preview",
                "action_type": "research",
                "target": {
                    "resource_type": "sandbox",
                    "resource_id": suffix,
                    "environment": "analysis",
                },
                "risk_class": "R0",
                "purpose": "Test reconstruction.",
                "evidence_refs": [evidence_id],
                "expected_preconditions": ["record exists"],
                "expected_postconditions": ["analysis is recorded"],
                "resource_impact": {
                    "currency": "USD",
                    "money_minor": 0,
                    "token_estimate": 0,
                    "compute_seconds_estimate": 0,
                    "relationship_risk": "none",
                    "data_classifications": ["internal"],
                },
                "rollback_or_compensation": {
                    "available": True,
                    "plan": "Discard analysis.",
                    "owner_id": "admin-123",
                    "deadline_seconds": 0,
                },
                "requested_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
            },
        )

        assert claim.status_code == 201, claim.text
        assert evidence.status_code == 201, evidence.text
        assert action.status_code == 201, action.text
        assert action.json()["action"]["status"] == "authorized"
        assert action.json()["audit_chain_valid"] is True
