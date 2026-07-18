"""Authenticated API tests for durable Venture Cell control administration."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import auth
from src.api.control_runtime import (
    ControlPlaneConfig,
    ControlRuntimeConfigurationError,
    build_control_plane_runtime,
    load_control_plane_config,
    reset_control_plane_runtime,
)
from src.api.main import app
from src.api.routes import control
from src.control import AutonomyStage, CellStatus
from src.control.models import utc_now


ROOT = "control-root"
REVIEWER = "control-reviewer"


@pytest.fixture(autouse=True)
def _isolate_runtime() -> None:
    app.dependency_overrides.clear()
    reset_control_plane_runtime()
    yield
    app.dependency_overrides.clear()
    reset_control_plane_runtime()


@pytest.fixture
def runtime(tmp_path: Path):
    config = ControlPlaneConfig(
        root_authority_id=ROOT,
        human_authority_ids=frozenset({ROOT, REVIEWER}),
        state_db_path=tmp_path / "control.db",
        evidence_ledger_path=tmp_path / "evidence.jsonl",
        max_grant_ttl_hours=24,
        max_approval_ttl_minutes=60,
    )
    built = build_control_plane_runtime(config)
    app.dependency_overrides[control.require_control_runtime] = lambda: built
    return built


@pytest.fixture
def client(monkeypatch, runtime) -> TestClient:
    monkeypatch.setattr(auth, "SECRET_KEY", "t" * 32)
    monkeypatch.setattr(auth, "JWT_ISSUER", "https://issuer.example.com")
    monkeypatch.setattr(auth, "JWT_AUDIENCE", "control-api-tests")
    return TestClient(app)


def _token(
    subject: str,
    permissions: list[str],
    *,
    role: str = "admin",
) -> str:
    return auth.create_access_token(
        {
            "sub": subject,
            "username": f"{subject}@example.com",
            "role": role,
            "permissions": permissions,
        }
    )


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _root_headers() -> dict[str, str]:
    return _headers(
        _token(
            ROOT,
            ["control:read", "control:root", "control:approve"],
        )
    )


def _cell_payload(cell_id: str = "cell-api") -> dict:
    return {
        "cell_id": cell_id,
        "mission": "Validate one bounded internal workflow.",
        "owner_id": ROOT,
        "allowed_geographies": ["US"],
        "allowed_data_classes": ["internal"],
        "prohibited_actions": ["constitutional.change_policy"],
        "max_daily_spend_usd": "25",
        "max_total_spend_usd": "100",
        "kill_conditions": ["critical policy bypass"],
    }


def _create_cell(client: TestClient, cell_id: str = "cell-api") -> None:
    response = client.post(
        "/api/v1/control/cells",
        json=_cell_payload(cell_id),
        headers=_root_headers(),
    )
    assert response.status_code == 201, response.text


def test_production_control_configuration_is_explicit(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CONTROL_ROOT_AUTHORITY_ID", ROOT)
    monkeypatch.setenv("CONTROL_HUMAN_AUTHORITY_IDS", REVIEWER)
    monkeypatch.delenv("CONTROL_STATE_DB_PATH", raising=False)
    monkeypatch.delenv("CONTROL_EVIDENCE_LEDGER_PATH", raising=False)

    with pytest.raises(
        ControlRuntimeConfigurationError,
        match="explicit control state",
    ):
        load_control_plane_config()

    monkeypatch.setenv("CONTROL_STATE_DB_PATH", "relative/control.db")
    monkeypatch.setenv("CONTROL_EVIDENCE_LEDGER_PATH", "relative/evidence.jsonl")
    with pytest.raises(ControlRuntimeConfigurationError, match="absolute"):
        load_control_plane_config()


def test_configured_root_creates_only_nonexecuting_initial_grant(
    client: TestClient,
    runtime,
) -> None:
    _create_cell(client)
    grant_payload = {
        "grant_id": "grant-api",
        "cell_id": "cell-api",
        "agent_id": "agent-api",
        "action_type": "update_venture_status",
        "initial_stage": "shadow",
        "resource_prefixes": ["venture:cell-api"],
        "expires_at": (utc_now() + timedelta(hours=4)).isoformat(),
        "context_fingerprint": "model-v1:prompt-v1:tools-v1",
        "allowed_geographies": ["US"],
        "allowed_data_classes": ["internal"],
    }
    response = client.post(
        "/api/v1/control/grants",
        json=grant_payload,
        headers=_root_headers(),
    )

    assert response.status_code == 201, response.text
    assert response.json()["stage"] == AutonomyStage.SHADOW
    assert runtime.policy.get_grant("grant-api").stage is AutonomyStage.SHADOW

    invalid = client.post(
        "/api/v1/control/grants",
        json={
            **grant_payload,
            "grant_id": "grant-bypass",
            "initial_stage": "bounded",
        },
        headers=_root_headers(),
    )
    assert invalid.status_code == 422
    assert runtime.policy.get_grant("grant-bypass") is None


def test_signed_admin_claim_cannot_self_declare_root(
    client: TestClient,
    runtime,
) -> None:
    intruder = _headers(
        _token(
            "unconfigured-admin",
            ["control:read", "control:root"],
        )
    )

    response = client.post(
        "/api/v1/control/cells",
        json=_cell_payload(),
        headers=intruder,
    )

    assert response.status_code == 403
    assert runtime.policy.get_cell("cell-api") is None


def test_human_can_pause_but_only_root_can_resume(
    client: TestClient,
    runtime,
) -> None:
    _create_cell(client)
    reviewer = _headers(
        _token(
            REVIEWER,
            ["control:approve", "control:root"],
        )
    )

    paused = client.post(
        "/api/v1/control/cells/cell-api/pause",
        json={"reason": "operator safety drill"},
        headers=reviewer,
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    denied = client.post(
        "/api/v1/control/cells/cell-api/resume",
        json={"reason": "attempted non-root resume"},
        headers=reviewer,
    )
    assert denied.status_code == 403
    assert runtime.policy.get_cell("cell-api").status is CellStatus.PAUSED

    resumed = client.post(
        "/api/v1/control/cells/cell-api/resume",
        json={"reason": "root completed the safety review"},
        headers=_root_headers(),
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "active"


def test_approval_identity_and_ttl_are_server_bound(
    client: TestClient,
    runtime,
) -> None:
    reviewer = _headers(
        _token(REVIEWER, ["control:approve", "control:read"])
    )
    response = client.post(
        "/api/v1/control/approvals",
        json={
            "approval_id": "approval-api",
            "action_fingerprint": "a" * 64,
            "expires_in_minutes": 30,
        },
        headers=reviewer,
    )

    assert response.status_code == 201, response.text
    assert response.json()["approver_id"] == REVIEWER
    stored = runtime.policy.export_state()["approvals"]
    assert stored[0]["approver_id"] == REVIEWER

    excessive = client.post(
        "/api/v1/control/approvals",
        json={
            "approval_id": "approval-too-long",
            "action_fingerprint": "b" * 64,
            "expires_in_minutes": 61,
        },
        headers=reviewer,
    )
    assert excessive.status_code == 422


def test_authorized_incident_reporter_can_only_reduce_authority(
    client: TestClient,
    runtime,
) -> None:
    _create_cell(client)
    reporter = _headers(
        _token(
            "safety-monitor",
            ["control:incident"],
            role="service",
        )
    )

    response = client.post(
        "/api/v1/control/incidents",
        json={
            "incident_id": "incident-api-critical",
            "cell_id": "cell-api",
            "severity": "critical",
            "reason": "possible policy bypass detected",
        },
        headers=reporter,
    )

    assert response.status_code == 201, response.text
    assert runtime.policy.get_cell("cell-api").status is CellStatus.PAUSED


def test_control_state_is_visible_after_runtime_reconstruction(
    client: TestClient,
    runtime,
) -> None:
    _create_cell(client, "cell-restart-api")

    restored = build_control_plane_runtime(runtime.config)

    assert restored.policy.get_cell("cell-restart-api") is not None
    assert restored.policy.persistence_healthy
    assert restored.policy.evidence_continuity
    assert restored.state_store.verify_integrity()
    assert restored.evidence_ledger.verify_chain()


def test_unconfigured_control_endpoint_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(auth, "SECRET_KEY", "u" * 32)
    monkeypatch.setattr(auth, "JWT_ISSUER", "https://issuer.example.com")
    monkeypatch.setattr(auth, "JWT_AUDIENCE", "control-api-tests")
    monkeypatch.delenv("CONTROL_ROOT_AUTHORITY_ID", raising=False)
    app.dependency_overrides.clear()
    reset_control_plane_runtime()
    client = TestClient(app)

    response = client.get(
        "/api/v1/control/status",
        headers=_headers(_token(ROOT, ["control:read"])),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Constitutional control plane unavailable"
