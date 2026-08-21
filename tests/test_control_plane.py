"""Security and reliability tests for bounded Venture Cell autonomy."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from src.control import (
    ActionIntent,
    ApprovalRecord,
    AssumptionRecord,
    AssumptionRegister,
    AssumptionStatus,
    AuthorizationError,
    AutonomyStage,
    CapabilityGrant,
    EvidenceLane,
    EvidenceOrigin,
    EvidenceReference,
    Incident,
    IncidentSeverity,
    PolicyDisposition,
    PromotionEvidence,
    VentureCellCharter,
    build_default_control_plane,
    minimum_zero_failure_trials,
    one_sided_failure_upper_bound,
)
from src.control.models import utc_now
from src.core.knowledge_graph import knowledge_graph
from src.core.knowledge_graph_connector import KnowledgeGraphConnector
from src.services.decision_engine import ActionSpec, ConditionNode, DecisionEngine, Rule


ROOT = "human-root"
HUMAN_ONE = "human-one"
HUMAN_TWO = "human-two"
CONTEXT = "model-v1:prompt-v3:toolset-v2"


def _plane(cell_id: str = "cell-1"):
    policy, gateway = build_default_control_plane(
        root_actor_id=ROOT,
        human_authorities={HUMAN_ONE, HUMAN_TWO},
    )
    policy.create_cell(
        ROOT,
        VentureCellCharter(
            cell_id=cell_id,
            mission="Validate and operate one bounded digital venture.",
            owner_id=ROOT,
            allowed_geographies=frozenset({"US"}),
            allowed_data_classes=frozenset({"public", "internal"}),
            max_daily_spend_usd=Decimal("100"),
            max_total_spend_usd=Decimal("500"),
            kill_conditions=("critical incident", "ledger integrity failure"),
        ),
    )
    return policy, gateway


def _grant(
    *,
    grant_id: str = "grant-1",
    cell_id: str = "cell-1",
    agent_id: str = "agent-1",
    action_type: str = "update_venture_status",
    stage: AutonomyStage = AutonomyStage.SUPERVISED_CANARY,
    resource_prefix: str | None = None,
    delegation_depth: int = 0,
    amount: Decimal = Decimal("0"),
) -> CapabilityGrant:
    return CapabilityGrant(
        grant_id=grant_id,
        cell_id=cell_id,
        agent_id=agent_id,
        action_type=action_type,
        stage=stage,
        resource_prefixes=(resource_prefix or f"venture:{cell_id}",),
        expires_at=utc_now() + timedelta(hours=4),
        context_fingerprint=CONTEXT,
        allowed_geographies=frozenset({"US"}),
        allowed_data_classes=frozenset({"public"}),
        max_per_action_usd=amount,
        max_daily_spend_usd=amount,
        max_total_spend_usd=amount,
        delegation_depth=delegation_depth,
    )


def _intent(
    *,
    action_id: str,
    cell_id: str = "cell-1",
    agent_id: str = "agent-1",
    action_type: str = "update_venture_status",
    amount: Decimal = Decimal("0"),
    context: str = CONTEXT,
    payload=None,
) -> ActionIntent:
    return ActionIntent(
        action_id=action_id,
        cell_id=cell_id,
        agent_id=agent_id,
        action_type=action_type,
        resource=f"venture:{cell_id}",
        payload=payload or {},
        amount_usd=amount,
        geography="US",
        data_classes=frozenset({"public"}),
        context_fingerprint=context,
    )


def test_wolfram_verified_zero_failure_thresholds() -> None:
    assert one_sided_failure_upper_bound(0, 5) == pytest.approx(0.4507197283)
    assert one_sided_failure_upper_bound(0, 10) == pytest.approx(0.2588655509)
    assert one_sided_failure_upper_bound(0, 299) == pytest.approx(0.00996914679)
    assert one_sided_failure_upper_bound(1, 100) == pytest.approx(0.04655981145)
    assert one_sided_failure_upper_bound(5, 100) == pytest.approx(0.10225337764)
    assert minimum_zero_failure_trials(0.10) == 29
    assert minimum_zero_failure_trials(0.03) == 99
    assert minimum_zero_failure_trials(0.01) == 299
    assert minimum_zero_failure_trials(0.001) == 2995


def test_assumption_register_rejects_internal_confidence_as_proof() -> None:
    policy, _ = _plane()
    register = AssumptionRegister(
        policy.ledger,
        independent_verifiers={ROOT},
    )
    register.register(
        "agent-research",
        AssumptionRecord(
            assumption_id="assumption-1",
            cell_id="cell-1",
            statement="Customers retain the workflow after onboarding.",
            why_it_matters="Retention is the venture viability gate.",
            cheapest_decisive_test="Observe retained product usage for 30 days.",
            consequence_if_false="Stop investment and revise the problem wedge.",
            test_deadline=utc_now() + timedelta(days=45),
            created_by="agent-research",
        ),
    )
    register.add_evidence(
        "agent-research",
        "assumption-1",
        EvidenceReference(
            evidence_id="simulation-1",
            lane=EvidenceLane.INTERNAL_CONTEXT,
            origin=EvidenceOrigin.INTERNAL_SIMULATION,
            source_reference="simulation://retention-v1",
            content_digest="sha256:simulation",
            observed_at=utc_now(),
        ),
    )
    with pytest.raises(AuthorizationError):
        register.transition(
            "agent-research",
            "assumption-1",
            AssumptionStatus.VALIDATED,
            "The simulation was positive.",
            verifier_id=ROOT,
        )

    register.add_evidence(
        "agent-research",
        "assumption-1",
        EvidenceReference(
            evidence_id="usage-1",
            lane=EvidenceLane.VENTURE_VIABILITY,
            origin=EvidenceOrigin.EXTERNAL_SYSTEM,
            source_reference="product-analytics://cohort-2026-07",
            content_digest="sha256:external-usage",
            observed_at=utc_now(),
        ),
    )
    validated = register.transition(
        "agent-research",
        "assumption-1",
        AssumptionStatus.VALIDATED,
        "The external cohort met the retained-usage gate.",
        verifier_id=ROOT,
    )
    assert validated.status is AssumptionStatus.VALIDATED


def test_shadow_grant_never_invokes_executor() -> None:
    policy, gateway = _plane()
    policy.issue_grant(ROOT, _grant(stage=AutonomyStage.SHADOW))
    calls = []
    gateway.register_executor("update_venture_status", calls.append)

    result = gateway.submit(_intent(action_id="shadow-1"))

    assert result.decision.disposition is PolicyDisposition.SHADOW
    assert result.receipt is None
    assert calls == []


def test_authorized_action_executes_once_and_returns_same_receipt() -> None:
    policy, gateway = _plane()
    policy.issue_grant(ROOT, _grant())
    calls = []
    gateway.register_executor(
        "update_venture_status",
        lambda intent: calls.append(intent.action_id) or {"id": "record-7"},
    )
    intent = _intent(action_id="execute-once")

    first = gateway.submit(intent)
    second = gateway.submit(intent)

    assert first.decision.disposition is PolicyDisposition.ALLOW
    assert first.receipt and first.receipt.status == "executed"
    assert second == first
    assert calls == ["execute-once"]
    assert policy.ledger.verify_chain()


def test_aggregate_budget_stops_transaction_splitting() -> None:
    policy, gateway = _plane()
    policy.issue_grant(
        ROOT,
        replace(
            _grant(
                action_type="spend_within_envelope",
                stage=AutonomyStage.BOUNDED,
                amount=Decimal("100"),
            ),
            max_per_action_usd=Decimal("60"),
        ),
    )
    gateway.register_executor("spend_within_envelope", lambda intent: {"id": intent.action_id})

    first = gateway.submit(
        _intent(
            action_id="spend-1",
            action_type="spend_within_envelope",
            amount=Decimal("60"),
        )
    )
    second = gateway.submit(
        _intent(
            action_id="spend-2",
            action_type="spend_within_envelope",
            amount=Decimal("50"),
        )
    )

    assert first.receipt and first.receipt.status == "executed"
    assert second.decision.disposition is PolicyDisposition.DENY
    assert second.decision.reason_codes == ("grant_daily_budget_exceeded",)


def test_changed_context_forces_capability_back_to_shadow() -> None:
    policy, gateway = _plane()
    policy.issue_grant(ROOT, _grant())
    gateway.register_executor("update_venture_status", lambda intent: {"id": "should-not-run"})

    result = gateway.submit(_intent(action_id="context-change", context="model-v2"))

    assert result.decision.disposition is PolicyDisposition.SHADOW
    assert result.decision.reason_codes == ("context_changed_revalidation_required",)


def test_material_action_needs_two_distinct_bound_human_approvals() -> None:
    policy, gateway = _plane()
    policy.issue_grant(
        ROOT,
        _grant(
            action_type="finance.transfer",
            stage=AutonomyStage.BOUNDED,
            amount=Decimal("50"),
        ),
    )
    gateway.register_executor("finance.transfer", lambda intent: {"id": "transfer-1"})
    intent = _intent(
        action_id="material-1",
        action_type="finance.transfer",
        amount=Decimal("25"),
        payload={"destination": "approved-vendor", "amount": "25"},
    )

    first_attempt = gateway.submit(intent)
    assert first_attempt.decision.disposition is PolicyDisposition.REVIEW
    for approval_id, approver in (("approval-1", HUMAN_ONE), ("approval-2", HUMAN_TWO)):
        policy.record_approval(
            ApprovalRecord(
                approval_id=approval_id,
                action_fingerprint=intent.fingerprint(),
                approver_id=approver,
                policy_version=policy.policy_version,
                expires_at=utc_now() + timedelta(minutes=10),
            )
        )

    result = gateway.submit(intent)
    assert result.decision.disposition is PolicyDisposition.ALLOW
    assert result.decision.valid_human_approvals == 2
    assert result.receipt and result.receipt.status == "executed"


def test_constitutional_action_is_denied_even_without_a_grant() -> None:
    policy, _ = _plane()
    result = policy.evaluate(
        _intent(
            action_id="constitution-1",
            action_type="constitutional.change_policy",
        )
    )
    assert result.disposition is PolicyDisposition.DENY
    assert result.reason_codes == ("constitutional_action_non_delegable",)


def test_child_grant_must_be_a_strict_subset() -> None:
    policy, _ = _plane()
    parent = policy.issue_grant(
        ROOT,
        _grant(
            grant_id="parent",
            agent_id="parent-agent",
            delegation_depth=1,
            amount=Decimal("50"),
            resource_prefix="venture:cell-1",
        ),
    )
    child = replace(
        _grant(
            grant_id="child",
            agent_id="child-agent",
            amount=Decimal("25"),
            resource_prefix="venture:cell-1:record:",
        ),
        expires_at=parent.expires_at - timedelta(hours=1),
    )

    installed = policy.delegate_grant("parent-agent", "parent", child)
    assert installed.parent_grant_id == "parent"
    assert installed.max_total_spend_usd < parent.max_total_spend_usd

    too_broad = replace(
        child,
        grant_id="child-broad",
        resource_prefixes=("venture:",),
    )
    with pytest.raises(AuthorizationError):
        policy.delegate_grant("parent-agent", "parent", too_broad)


def test_promotion_uses_assurance_evidence_and_moves_one_stage() -> None:
    policy, _ = _plane()
    policy.issue_grant(ROOT, _grant(stage=AutonomyStage.SHADOW))
    evidence = PromotionEvidence(
        trials=29,
        failures=0,
        observation_days=7,
        audit_completeness=1.0,
        rollback_drills=1,
        policy_violations=0,
        critical_incidents=0,
        red_team_critical_findings=0,
        context_fingerprint=CONTEXT,
    )

    evaluation = policy.promote_grant(ROOT, "grant-1", evidence, "review-2026-07")

    assert evaluation.passed
    assert evaluation.failure_upper_bound < 0.10
    assert policy.get_grant("grant-1").stage is AutonomyStage.SUPERVISED_CANARY


def test_major_incident_regresses_and_critical_incident_pauses_cell() -> None:
    policy, _ = _plane()
    policy.issue_grant(ROOT, _grant(stage=AutonomyStage.BOUNDED))
    policy.report_incident(
        Incident(
            incident_id="incident-major",
            cell_id="cell-1",
            severity=IncidentSeverity.MAJOR,
            reason="adapter returned an inconsistent receipt",
            actor_id="monitor",
            grant_id="grant-1",
        )
    )
    assert policy.get_grant("grant-1").stage is AutonomyStage.SUPERVISED_CANARY

    policy.report_incident(
        Incident(
            incident_id="incident-critical",
            cell_id="cell-1",
            severity=IncidentSeverity.CRITICAL,
            reason="possible policy bypass",
            actor_id="monitor",
        )
    )
    assert policy.get_cell("cell-1").status.value == "paused"
    assert policy.evaluate(_intent(action_id="paused-1")).disposition is PolicyDisposition.DENY


def test_parameter_constraints_are_enforced_before_adapter_execution() -> None:
    policy, gateway = _plane()
    policy.issue_grant(
        ROOT,
        replace(
            _grant(),
            parameter_constraints={"parameters.new_status": ("Needs Review",)},
        ),
    )
    calls = []
    gateway.register_executor("update_venture_status", calls.append)
    result = gateway.submit(
        _intent(
            action_id="bad-parameter",
            payload={"parameters": {"new_status": "Delete Everything"}},
        )
    )
    assert result.decision.disposition is PolicyDisposition.DENY
    assert result.decision.reason_codes == ("parameter_outside_grant",)
    assert calls == []


def test_decision_engine_executes_only_through_a_matching_capability() -> None:
    cell_id = "venture-controlled"
    policy, gateway = _plane(cell_id)
    policy.issue_grant(
        ROOT,
        replace(
            _grant(
                cell_id=cell_id,
                agent_id="decision-engine",
                resource_prefix=f"venture:{cell_id}",
            ),
            parameter_constraints={"parameters.new_status": ("Triggered",)},
        ),
    )
    rule = Rule(
        rule_id="controlled-rule",
        name="Controlled status update",
        venture_type="DigitalVenture",
        condition=ConditionNode.from_dict(
            {"metric": "x", "operator": "greater_than", "value": 0.5}
        ),
        action=ActionSpec(
            type="update_venture_status",
            parameters={"new_status": "Triggered"},
        ),
    )
    engine = DecisionEngine(
        [rule],
        connector=KnowledgeGraphConnector(),
        gateway=gateway,
        context_fingerprint=CONTEXT,
    )

    outcome = engine.evaluate(cell_id, "DigitalVenture", {"x": 0.9})[0]

    assert outcome["execution_status"] == "executed"
    assert outcome["policy_disposition"] == "allow"
    assert knowledge_graph.get_node(cell_id).properties["status"] == "Triggered"
