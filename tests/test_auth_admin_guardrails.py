"""Authentication and human-administration boundary tests."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api import auth
from src.api.admin_audit import (
    admin_audit_ledger,
    record_admin_intent,
    record_admin_outcome,
)
from src.database.connection import db


def test_missing_token_never_defaults_to_admin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.get_current_user(None))
    assert exc_info.value.status_code == 401


def test_demo_auth_requires_explicit_nonproduction_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_DEMO_AUTH", "false")
    assert auth.authenticate_user("admin", "admin") is None

    monkeypatch.setenv("ALLOW_DEMO_AUTH", "true")
    assert auth.authenticate_user("admin", "admin")["role"] == "admin"

    monkeypatch.setenv("ENVIRONMENT", "production")
    assert auth.authenticate_user("admin", "admin") is None


def test_production_rejects_default_or_short_jwt_secret(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_DEMO_AUTH", "false")
    monkeypatch.setattr(auth, "SECRET_KEY", "change-me")
    with pytest.raises(RuntimeError, match=r"32\+"):
        auth.validate_auth_configuration()


def test_human_admin_dependency_rejects_ordinary_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            auth.require_admin_user(
                {
                    "user_id": "user-1",
                    "role": "user",
                    "permissions": ["read"],
                }
            )
        )
    assert exc_info.value.status_code == 403

    accepted = asyncio.run(
        auth.require_admin_user(
            {
                "user_id": "human-admin-1",
                "role": "admin",
                "permissions": ["read", "write", "admin"],
            }
        )
    )
    assert accepted["user_id"] == "human-admin-1"


def test_mutating_api_route_rejects_anonymous_call_before_database_use() -> None:
    from src.api.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/ventures/",
        json={
            "name": "Unauthorized venture",
            "venture_type": "saas",
            "initial_investment": 0,
        },
    )
    assert response.status_code == 401


def test_admin_audit_intent_and_outcome_share_a_valid_hash_chain() -> None:
    human = {
        "user_id": "human-admin-audit",
        "role": "admin",
        "permissions": ["admin"],
    }
    action_id = record_admin_intent(
        human,
        action_type="admin.agent.deactivate",
        resource="agent:agent-7",
        changed_fields=("is_active",),
    )
    record_admin_outcome(
        human,
        action_id=action_id,
        action_type="admin.agent.deactivate",
        resource="agent:agent-7",
        status="succeeded",
    )

    assert admin_audit_ledger.verify_chain()
    assert admin_audit_ledger.entries[-2].action_id == action_id
    assert admin_audit_ledger.entries[-1].action_id == action_id


def test_schema_drop_has_no_unlocked_default(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_SCHEMA_DROP", raising=False)
    monkeypatch.delenv("DATABASE_DROP_CONFIRMATION", raising=False)
    with pytest.raises(PermissionError, match="break|schema drop"):
        db.drop_tables(confirmation_token="not-authorized")
