"""Audit regressions: real dependencies, no authentication dependency overrides."""
import asyncio
import importlib
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from tests.fixtures.auth import KEY, configure, token

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def configured(monkeypatch):
    configure(monkeypatch)
    return importlib.import_module("src.api.auth")


@pytest.mark.parametrize("value", [None, "demo", "demo_token", "arbitrary-text", "stub-token"])
def test_anonymous_and_literal_identities_rejected(configured, value):
    with pytest.raises(HTTPException) as err:
        asyncio.run(configured.get_current_user(value))
    assert err.value.status_code == 401


def test_signed_identity_is_not_a_demo_lookup(configured):
    principal = asyncio.run(configured.get_current_user(token()))
    assert principal["user_id"] == "daleobanks"
    assert principal["role"] == "user"


@pytest.mark.parametrize("claims", [
    {"exp": 1}, {"iss": "wrong"}, {"aud": "wrong"}, {"sub": ""},
    {"exp": None}, {"exp": "99999999999"}, {"exp": True},
    {"role": []}, {"permissions": "admin"}, {"username": []},
])
def test_bad_claims_rejected(configured, claims):
    assert configured.verify_token(token(**claims)) is None


@pytest.mark.parametrize("missing", ["exp", "sub", "iss", "aud"])
def test_required_claims(configured, missing):
    claims = jwt.get_unverified_claims(token())
    claims.pop(missing)
    assert configured.verify_token(jwt.encode(claims, KEY, algorithm="HS256")) is None


def test_wrong_algorithm_and_key(configured):
    claims = jwt.get_unverified_claims(token())
    assert configured.verify_token(jwt.encode(claims, KEY, algorithm="HS384")) is None
    assert configured.verify_token(jwt.encode(claims, "wrong-key", algorithm="HS256")) is None


def test_unsigned_algorithm_rejected(configured):
    import base64
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
    unsigned = header + "." + token().split(".")[1] + "."
    assert configured.verify_token(unsigned) is None


@pytest.mark.parametrize("key", ["", "change-me", "your-secret-key-change-in-production", " " * 40])
def test_unsafe_configuration_rejected(configured, monkeypatch, key):
    monkeypatch.setenv("JWT_SECRET_KEY", key)
    with pytest.raises(RuntimeError):
        configured.validate_auth_configuration()


def test_transport_refuses_missing_key_and_explicit_unsigned(configured, monkeypatch):
    from src.services.bridge_security import (
        BridgeSecurityError,
        NonceCache,
        verify_headers,
    )
    monkeypatch.delenv("WEALTHMACHINE_SIGNING_KEY")
    for flag in [None, True, False]:
        with pytest.raises(BridgeSecurityError):
            verify_headers({}, b"{}", nonce_cache=NonceCache(), require_signature=flag)


@pytest.mark.parametrize("missing", ["JWT_SECRET_KEY", "JWT_ISSUER", "JWT_AUDIENCE"])
def test_missing_configuration_fails_closed(configured, monkeypatch, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(RuntimeError):
        configured.validate_auth_configuration()
    with pytest.raises(HTTPException) as err:
        asyncio.run(configured.get_current_user(token()))
    assert err.value.status_code == 503


@pytest.mark.parametrize("path", ["/api/opportunities/intake", "/api/ventures/evaluate",
                                "/api/v1/ventures/"])
def test_protected_routes_reject_literals(configured, path):
    from src.api.main import app
    client = TestClient(app)
    method = client.post if path != "/api/v1/ventures/" else client.get
    for value in [None, "demo", "demo_token", "stub-token", "arbitrary-text"]:
        headers = {} if value is None else {"Authorization": f"Bearer {value}"}
        assert method(path, headers=headers).status_code == 401


def test_root_is_same_application(configured):
    from src.api.main import app
    assert importlib.import_module("main").app is app


def test_stub_and_demo_issuer_not_importable(configured):
    assert not (ROOT / "jwt.py").exists()
    for name in ["DEMO_USERS", "authenticate_user", "create_access_token"]:
        assert not hasattr(configured, name)


def test_missing_transport_key_fails_even_with_dev_flags(configured, monkeypatch):
    from src.api.main import app
    from tests.test_opportunity_intake import fire_packet
    monkeypatch.delenv("WEALTHMACHINE_SIGNING_KEY")
    monkeypatch.setenv("UNIIMENTE_BRIDGE_DEV_UNSIGNED", "1")
    monkeypatch.setenv("ALLOW_DEMO_AUTH", "true")
    response = TestClient(app).post("/api/opportunities/intake", json=fire_packet(),
                                    headers={"Authorization": f"Bearer {token()}"})
    assert response.status_code in (401, 503)


def test_missing_jose_never_loads_demo(configured):
    # A fresh process must propagate missing dependency; no fallback application.
    script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'jose' or name.startswith('jose.'):
        raise ImportError('injected missing jose')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import main
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                            capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode != 0
    assert "injected missing jose" in result.stderr


def test_container_source_allowlist():
    docker = (ROOT / "Dockerfile").read_text()
    assert "COPY . ." not in docker
    assert "COPY src ./src" in docker
    assert "COPY contracts ./contracts" in docker
