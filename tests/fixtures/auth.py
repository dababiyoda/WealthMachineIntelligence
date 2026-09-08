"""Synthetic test-only credentials; never shipped in the application image."""
import time
import tempfile
import json

from fastapi.testclient import TestClient
from jose import jwt

from src.services.bridge_security import build_headers

KEY = "synthetic-test-only-jwt-key-not-for-production-2026"
BRIDGE_KEY = "synthetic-test-only-transport-key-2026"


def configure(monkeypatch):
    from src.services.bridge_state import close_bridge_state
    close_bridge_state()
    monkeypatch.setenv("JWT_SECRET_KEY", KEY)
    monkeypatch.setenv("JWT_ISSUER", "wmi-test-issuer")
    monkeypatch.setenv("JWT_AUDIENCE", "wmi-test-api")
    monkeypatch.setenv("WEALTHMACHINE_SIGNING_KEY", BRIDGE_KEY)
    monkeypatch.setenv('UNIIMENTE_BRIDGE_MODE', 'synthetic-localhost')
    monkeypatch.setenv('UNIIMENTE_BRIDGE_STATE_PATH', tempfile.mkdtemp(prefix='wmi-fixture-') + '/bridge.jsonl')
    monkeypatch.setenv('UNIIMENTE_CONSTITUTION_HASH', 'sha256:' + 'a' * 64)
    monkeypatch.setenv('UNIIMENTE_LEGAL_PRINCIPAL', 'alfonso_lopez')


def token(**changes):
    claims = {"sub": "daleobanks", "username": "synthetic-service", "role": "user",
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
                schema_version=json.loads(request.content).get('schema_version', '1.0')))
        elif request.method == 'GET' and request.url.path.endswith('/assessment'):
            assessment_id = request.url.path.split('/')[-2]
            request.headers.update(build_headers(b'', identity='daleobanks', schema_version='1.1',
                operation='assessment.get:' + assessment_id))
        return request
