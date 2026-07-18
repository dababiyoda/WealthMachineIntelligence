"""Authentication and human-administration boundary tests."""

from __future__ import annotations

import asyncio
from datetime import timedelta

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


def test_production_requires_explicit_issuer_and_audience(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_DEMO_AUTH", "false")
    monkeypatch.setattr(auth, "SECRET_KEY", "s" * 32)
    monkeypatch.setattr(auth, "JWT_ISSUER", "wealthmachine-local")
    monkeypatch.setattr(auth, "JWT_AUDIENCE", "wealthmachine-api")
    with pytest.raises(RuntimeError, match="JWT_ISSUER"):
        auth.validate_auth_configuration()

    monkeypatch.setattr(auth, "JWT_ISSUER", "https://identity.example.com")
    with pytest.raises(RuntimeError, match="JWT_AUDIENCE"):
        auth.validate_auth_configuration()

    monkeypatch.setattr(auth, "JWT_AUDIENCE", "wealthmachine-production-api")
    auth.validate_auth_configuration()


def test_signed_admin_claims_resolve_without_demo_user_lookup(monkeypatch) -> None:
    monkeypatch.setattr(auth, "SECRET_KEY", "a" * 32)
    monkeypatch.setattr(auth, "JWT_ISSUER", "https://issuer.example.com")
    monkeypatch.setattr(auth, "JWT_AUDIENCE", "wealthmachine-api-tests")
    token = auth.create_access_token(
        {
            "sub": "production-human-7",
            "username": "operator@example.com",
            "role": "admin",
            "permissions": ["read", "admin"],
        }
    )

    principal = asyncio.run(auth.get_current_user(token))
    authorized = asyncio.run(auth.require_admin_user(principal))

    assert authorized == {
        "user_id": "production-human-7",
        "username": "operator@example.com",
        "role": "admin",
        "permissions": ["read", "admin"],
    }


def test_tampered_expired_and_wrong_audience_tokens_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(auth, "SECRET_KEY", "b" * 32)
    monkeypatch.setattr(auth, "JWT_ISSUER", "https://issuer.example.com")
    monkeypatch.setattr(auth, "JWT_AUDIENCE", "wealthmachine-api-tests")
    claims = {
        "sub": "human-8",
        "role": "user",
        "permissions": ["read"],
    }
    valid = auth.create_access_token(claims)
    header, payload, signature = valid.split(".")
    changed_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered = ".".join((header, payload, changed_signature))

    expired = auth.create_access_token(
        claims,
        expires_delta=timedelta(seconds=-1),
    )
    wrong_audience = auth.jwt.encode(
        {
            "sub": "human-8",
            "role": "user",
            "permissions": ["read"],
            "iss": auth.JWT_ISSUER,
            "aud": "some-other-service",
            "exp": auth.datetime.now(auth.timezone.utc) + timedelta(minutes=5),
        },
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )

    assert auth.verify_token(valid)["user_id"] == "human-8"
    assert auth.verify_token(tampered) is None
    assert auth.verify_token(expired) is None
    assert auth.verify_token(wrong_audience) is None


def test_token_creation_rejects_malformed_authority_claims(monkeypatch) -> None:
    monkeypatch.setattr(auth, "SECRET_KEY", "c" * 32)
    with pytest.raises(ValueError, match="subject"):
        auth.create_access_token({"role": "admin", "permissions": ["admin"]})
    with pytest.raises(ValueError, match="permissions"):
        auth.create_access_token(
            {"sub": "human-9", "role": "admin", "permissions": "admin"}
        )


def test_production_requires_an_explicit_host_allowlist(monkeypatch) -> None:
    from src.api import main as api_main

    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    with pytest.raises(RuntimeError, match="ALLOWED_HOSTS"):
        api_main._configured_trusted_hosts("production")

    monkeypatch.setenv("ALLOWED_HOSTS", "*")
    with pytest.raises(RuntimeError, match="cannot contain"):
        api_main._configured_trusted_hosts("production")

    monkeypatch.setenv("ALLOWED_HOSTS", "api.example.com, health.example.com")
    assert api_main._configured_trusted_hosts("production") == [
        "api.example.com",
        "health.example.com",
    ]


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
