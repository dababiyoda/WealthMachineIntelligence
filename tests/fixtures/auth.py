"""Synthetic test-only credentials; never shipped in the application image."""
import time

from fastapi.testclient import TestClient
from jose import jwt

from src.services.bridge_security import build_headers

KEY = "synthetic-test-only-jwt-key-not-for-production-2026"
BRIDGE_KEY = "synthetic-test-only-transport-key-2026"


def configure(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", KEY)
    monkeypatch.setenv("JWT_ISSUER", "wmi-test-issuer")
    monkeypatch.setenv("JWT_AUDIENCE", "wmi-test-api")
    monkeypatch.setenv("WEALTHMACHINE_SIGNING_KEY", BRIDGE_KEY)


def token(**changes):
    claims = {"sub": "synthetic-service", "username": "synthetic-service", "role": "user",
              "permissions": ["read"], "iss": "wmi-test-issuer", "aud": "wmi-test-api",
              "exp": int(time.time()) + 120}
    claims.update(changes)
    return jwt.encode(claims, KEY, algorithm="HS256")


class SyntheticBridgeClient(TestClient):
    """Real JWT and HMAC through real dependencies, not an auth override."""
    def build_request(self, *args, **kwargs):
        request = super().build_request(*args, **kwargs)
        request.headers.setdefault("Authorization", f"Bearer {token()}")
        if request.method == "POST":
            request.headers.update(build_headers(request.content, identity="daleobanks",
                                                schema_version="1.0"))
        return request
