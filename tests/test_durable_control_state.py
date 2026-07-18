"""Restart and tamper tests for durable control-plane state."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from src.control import (
    ActionIntent,
    ApprovalRecord,
    AuthorizationError,
    AutonomyStage,
    CapabilityGrant,
    CellStatus,
    EvidenceLedger,
    PolicyConfigurationError,
    PolicyDisposition,
    PromotionEvidence,
    SQLiteControlStateStore,
    StateIntegrityError,
    VentureCellCharter,
    build_default_control_plane,
)
from src.control.models import utc_now


ROOT = "human-root"
HUMAN_ONE = "human-one"
HUMAN_TWO = "human-two"
CELL_ID = "durable-cell"
AGENT_ID = "durable-agent"
CONTEXT = "model-v1:prompt-v3:tools-v2"


def _build(path: Path, *, ledger_path: Path | None = None):
    store = SQLiteControlStateStore(path)
    policy, gateway = build_default_control_plane(
        root_actor_id=ROOT,
        human_authorities={HUMAN_ONE, HUMAN_TWO},
        evidence_ledger=EvidenceLedger(ledger_path) if ledger_path else None,
        state_store=store,
    )
    return store, policy, gateway


def _provision(
    path: Path,
    *,
    action_type: str = "update_venture_status",
    stage: AutonomyStage = AutonomyStage.SUPERVISED_CANARY,
    max_per_action: Decimal = Decimal("100"),
    max_daily: Decimal = Decimal("100"),
    max_total: Decimal = Decimal("500"),
    ledger_path: Path | None = None,
):
    store, policy, gateway = _build(path, ledger_path=ledger_path)
    policy.create_cell(
        ROOT,
        VentureCellCharter(
            cell_id=CELL_ID,
            mission="Operate one bounded venture with restart-safe controls.",
            owner_id=ROOT,
            allowed_geographies=frozenset({"US"}),
            allowed_data_classes=frozenset({"public"}),
            max_daily_spend_usd=Decimal("200"),
            max_total_spend_usd=Decimal("1000"),
            kill_conditions=("critical incident", "state integrity failure"),
        ),
    )
    grant = policy.issue_grant(
        ROOT,
        CapabilityGrant(
            grant_id="durable-grant",
            cell_id=CELL_ID,
            agent_id=AGENT_ID,
            action_type=action_type,
            stage=min(stage, AutonomyStage.SHADOW),
            resource_prefixes=(f"venture:{CELL_ID}",),
            expires_at=utc_now() + timedelta(days=1),
            context_fingerprint=CONTEXT,
            allowed_geographies=frozenset({"US"}),
            allowed_data_classes=frozenset({"public"}),
            max_per_action_usd=max_per_action,
            max_daily_spend_usd=max_daily,
            max_total_spend_usd=max_total,
        ),
    )
    proof_by_stage = {
        AutonomyStage.SUPERVISED_CANARY: (29, 7, 1),
        AutonomyStage.BOUNDED: (99, 14, 2),
        AutonomyStage.SCALED_BOUNDED: (299, 30, 3),
    }
    while grant.stage < stage:
        next_stage = AutonomyStage(grant.stage + 1)
        trials, observation_days, rollback_drills = proof_by_stage[next_stage]
        evaluation = policy.promote_grant(
            ROOT,
            grant.grant_id,
            PromotionEvidence(
                trials=trials,
                failures=0,
                observation_days=observation_days,
                audit_completeness=1.0,
                rollback_drills=rollback_drills,
                policy_violations=0,
                critical_incidents=0,
                red_team_critical_findings=0,
                context_fingerprint=CONTEXT,
            ),
            independent_review_id=(
                f"test-review:{grant.grant_id}:{next_stage.name}"
            ),
        )
        assert evaluation.passed
        grant = policy.get_grant(grant.grant_id)
        assert grant is not None
    return store, policy, gateway


def _intent(
    action_id: str,
    *,
    action_type: str = "update_venture_status",
    amount: Decimal = Decimal("0"),
    payload: dict | None = None,
) -> ActionIntent:
    return ActionIntent(
        action_id=action_id,
        cell_id=CELL_ID,
        agent_id=AGENT_ID,
        action_type=action_type,
        resource=f"venture:{CELL_ID}",
        payload=payload or {},
        amount_usd=amount,
        geography="US",
        data_classes=frozenset({"public"}),
        context_fingerprint=CONTEXT,
    )


def test_completed_action_returns_same_receipt_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    store, first_policy, first_gateway = _provision(path)
    first_calls: list[str] = []
    first_gateway.register_executor(
        "update_venture_status",
        lambda intent: first_calls.append(intent.action_id)
        or {"id": "venture-record-1", "status": "validated"},
    )
    intent = _intent("restart-once")

    first = first_gateway.submit(intent)
    assert first.receipt and first.receipt.status == "executed"
    assert first_calls == ["restart-once"]
    assert store.verify_integrity()

    _, restored_policy, restored_gateway = _build(path)
    replay_calls: list[str] = []
    restored_gateway.register_executor(
        "update_venture_status",
        lambda submitted: replay_calls.append(submitted.action_id),
    )

    replay = restored_gateway.submit(intent)

    assert replay == first
    assert replay_calls == []
    assert restored_policy.get_cell(CELL_ID) == first_policy.get_cell(CELL_ID)
    assert restored_policy.get_grant("durable-grant") == first_policy.get_grant(
        "durable-grant"
    )


def test_rich_adapter_result_has_same_canonical_shape_after_restart(
    tmp_path: Path,
) -> None:
    @dataclass(frozen=True)
    class AdapterDetail:
        label: str
        count: int

    path = tmp_path / "control.db"
    _, _, gateway = _provision(path)
    observed_at = datetime(2026, 7, 18, 12, 30, tzinfo=timezone.utc)
    gateway.register_executor(
        "update_venture_status",
        lambda intent: {
            "amount": Decimal("12.50"),
            "observed_at": observed_at,
            "steps": ("validated", 2),
            "detail": AdapterDetail("pilot", 3),
            7: "non-string-key",
        },
    )
    intent = _intent("canonical-result-replay")

    first = gateway.submit(intent)
    assert first.result == {
        "7": "non-string-key",
        "amount": "12.50",
        "detail": {"count": 3, "label": "pilot"},
        "observed_at": observed_at.isoformat(),
        "steps": ["validated", 2],
    }

    _, _, restored_gateway = _build(path)
    calls: list[str] = []
    restored_gateway.register_executor(
        "update_venture_status",
        lambda submitted: calls.append(submitted.action_id),
    )
    replay = restored_gateway.submit(intent)

    assert replay == first
    assert calls == []


def test_spend_counters_survive_restart_and_stop_splitting(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    _, _, first_gateway = _provision(
        path,
        action_type="spend_within_envelope",
        stage=AutonomyStage.BOUNDED,
        max_per_action=Decimal("60"),
        max_daily=Decimal("100"),
        max_total=Decimal("100"),
    )
    first_gateway.register_executor(
        "spend_within_envelope",
        lambda intent: {"id": intent.action_id},
    )
    spent = first_gateway.submit(
        _intent(
            "spend-before-restart",
            action_type="spend_within_envelope",
            amount=Decimal("60"),
        )
    )
    assert spent.receipt and spent.receipt.status == "executed"

    _, _, restored_gateway = _build(path)
    calls: list[str] = []
    restored_gateway.register_executor(
        "spend_within_envelope",
        lambda intent: calls.append(intent.action_id),
    )
    blocked = restored_gateway.submit(
        _intent(
            "spend-after-restart",
            action_type="spend_within_envelope",
            amount=Decimal("50"),
        )
    )

    assert blocked.decision.disposition is PolicyDisposition.DENY
    assert blocked.decision.reason_codes == ("grant_daily_budget_exceeded",)
    assert calls == []


def test_exact_human_approvals_survive_restart(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    _, policy, gateway = _provision(
        path,
        action_type="finance.transfer",
        stage=AutonomyStage.BOUNDED,
        max_per_action=Decimal("100"),
        max_daily=Decimal("100"),
        max_total=Decimal("100"),
    )
    intent = _intent(
        "approved-after-restart",
        action_type="finance.transfer",
        amount=Decimal("25"),
        payload={"destination": "approved-vendor", "amount": "25"},
    )
    assert gateway.submit(intent).decision.disposition is PolicyDisposition.REVIEW
    for approval_id, approver in (
        ("durable-approval-1", HUMAN_ONE),
        ("durable-approval-2", HUMAN_TWO),
    ):
        policy.record_approval(
            ApprovalRecord(
                approval_id=approval_id,
                action_fingerprint=intent.fingerprint(),
                approver_id=approver,
                policy_version=policy.policy_version,
                expires_at=utc_now() + timedelta(hours=1),
            )
        )

    _, _, restored_gateway = _build(path)
    restored_gateway.register_executor(
        "finance.transfer",
        lambda submitted: {"id": f"transfer:{submitted.action_id}"},
    )
    result = restored_gateway.submit(intent)

    assert result.decision.disposition is PolicyDisposition.ALLOW
    assert result.decision.valid_human_approvals == 2
    assert result.receipt and result.receipt.status == "executed"


def test_inflight_action_requires_reconciliation_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    store, _, _ = _provision(path)
    intent = _intent("uncertain-downstream-outcome")
    fingerprint = intent.fingerprint()
    store.reserve_action(intent.action_id, fingerprint)
    assert store.mark_inflight(intent.action_id, fingerprint)

    _, _, restored_gateway = _build(path)
    calls: list[str] = []
    restored_gateway.register_executor(
        "update_venture_status",
        lambda submitted: calls.append(submitted.action_id),
    )
    result = restored_gateway.submit(intent)

    assert result.decision.disposition is PolicyDisposition.DENY
    assert result.decision.reason_codes == (
        "reconciliation_required_for_inflight_action",
    )
    assert calls == []


def test_idempotency_conflict_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    _, _, gateway = _provision(path)
    gateway.register_executor(
        "update_venture_status",
        lambda intent: {"id": intent.action_id},
    )
    original = _intent("durable-idempotency", payload={"status": "pilot"})
    assert gateway.submit(original).receipt is not None

    _, _, restored_gateway = _build(path)
    calls: list[str] = []
    restored_gateway.register_executor(
        "update_venture_status",
        lambda submitted: calls.append(submitted.action_id),
    )
    changed = replace(original, payload={"status": "scaled"})
    result = restored_gateway.submit(changed)

    assert result.decision.disposition is PolicyDisposition.DENY
    assert result.decision.reason_codes == ("idempotency_key_conflict",)
    assert calls == []


def test_failed_adapter_is_not_reinvoked_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    _, _, gateway = _provision(path)
    first_calls: list[str] = []

    def fail_once(intent: ActionIntent) -> None:
        first_calls.append(intent.action_id)
        raise RuntimeError("simulated adapter failure")

    gateway.register_executor("update_venture_status", fail_once)
    intent = _intent("durable-adapter-failure")
    first = gateway.submit(intent)
    assert first.receipt and first.receipt.status == "failed"
    assert first_calls == [intent.action_id]

    _, _, restored_gateway = _build(path)
    replay_calls: list[str] = []
    restored_gateway.register_executor(
        "update_venture_status",
        lambda submitted: replay_calls.append(submitted.action_id),
    )
    replay = restored_gateway.submit(intent)

    assert replay == first
    assert replay_calls == []


def test_pause_and_authority_identity_survive_restart(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    _, policy, _ = _provision(path)
    policy.pause_cell(HUMAN_ONE, CELL_ID, "operator drill")

    _, restored_policy, _ = _build(path)
    assert restored_policy.get_cell(CELL_ID).status is CellStatus.PAUSED
    assert restored_policy.evaluate(_intent("paused-after-restart")).reason_codes == (
        "cell_paused",
    )

    with pytest.raises(PolicyConfigurationError, match="root authorities"):
        build_default_control_plane(
            root_actor_id="different-root",
            human_authorities={HUMAN_ONE, HUMAN_TWO},
            state_store=SQLiteControlStateStore(path),
        )


def test_promotion_requires_reconstructed_evidence_continuity(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    _, _, _ = _provision(path, stage=AutonomyStage.SHADOW)
    _, restored_policy, _ = _build(path)
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

    with pytest.raises(AuthorizationError, match="ledger continuity"):
        restored_policy.promote_grant(
            ROOT,
            "durable-grant",
            evidence,
            independent_review_id="review-with-missing-history",
        )


def test_durable_evidence_chain_allows_evidence_gated_promotion(
    tmp_path: Path,
) -> None:
    path = tmp_path / "control.db"
    ledger_path = tmp_path / "evidence.jsonl"
    _provision(
        path,
        stage=AutonomyStage.SHADOW,
        ledger_path=ledger_path,
    )

    _, restored_policy, _ = _build(path, ledger_path=ledger_path)
    result = restored_policy.promote_grant(
        ROOT,
        "durable-grant",
        PromotionEvidence(
            trials=29,
            failures=0,
            observation_days=7,
            audit_completeness=1.0,
            rollback_drills=1,
            policy_violations=0,
            critical_incidents=0,
            red_team_critical_findings=0,
            context_fingerprint=CONTEXT,
        ),
        independent_review_id="durable-independent-review",
    )

    assert result.passed
    assert restored_policy.get_grant("durable-grant").stage is (
        AutonomyStage.SUPERVISED_CANARY
    )
    assert EvidenceLedger(ledger_path).verify_chain()


def test_policy_snapshot_and_gateway_records_detect_tampering(tmp_path: Path) -> None:
    path = tmp_path / "control.db"
    store, _, _ = _provision(path)
    intent = _intent("tampered-action")
    store.reserve_action(intent.action_id, intent.fingerprint())

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE gateway_actions SET lifecycle = 'completed' WHERE action_id = ?",
            (intent.action_id,),
        )
    with pytest.raises(StateIntegrityError):
        store.load_action(intent.action_id)
    assert not store.verify_integrity()

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE policy_snapshot SET payload = ? WHERE singleton = 1",
            ('{"schema_version":1}',),
        )
    with pytest.raises(StateIntegrityError):
        SQLiteControlStateStore(path).load_policy_state()
    with pytest.raises(StateIntegrityError):
        store.save_policy_state({"schema_version": 1, "replacement": True})
