"""Local subprocess evidence for Docker's exact CMD and COPY composition.

Not an image-build, deployment, real founder identity or external outcome test.
No route/dependency overrides; SQLite and signing material are synthetic fixtures.
"""
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from jose import jwt

from tests.fixtures.auth import BRIDGE_KEY, KEY, token
from tests.test_opportunity_intake import fire_packet
from tests.test_signed_bridge import _signed_headers

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def package(tmp_path):
    docker = (ROOT / "Dockerfile").read_text().splitlines()
    for line in docker:
        if line.startswith("COPY "):
            _, source, target = line.split()
            destination = tmp_path / target.removeprefix("./")
            if (ROOT / source).is_dir():
                shutil.copytree(ROOT / source, destination,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                if target in ("./", "."):
                    destination = tmp_path / source
                shutil.copy2(ROOT / source, destination)
    command = json.loads(next(line[4:] for line in docker if line.startswith("CMD ")))
    assert command == ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "5000"]
    environment = os.environ.copy()
    environment.update(DATABASE_URL=f"sqlite:///{tmp_path}/synthetic.db",
                       JWT_SECRET_KEY=KEY, JWT_ISSUER="wmi-test-issuer",
                       JWT_AUDIENCE="wmi-test-api", WEALTHMACHINE_SIGNING_KEY=BRIDGE_KEY,
                       PYTHONDONTWRITEBYTECODE="1", ENVIRONMENT="production")
    environment.update(UNIIMENTE_BRIDGE_MODE='synthetic-localhost',
        UNIIMENTE_BRIDGE_STATE_PATH=str(tmp_path / 'bridge.jsonl'),
        UNIIMENTE_CONSTITUTION_HASH='sha256:' + 'a' * 64, UNIIMENTE_LEGAL_PRINCIPAL='alfonso_lopez')
    assert not (tmp_path / "jwt.py").exists()
    assert not (tmp_path / "tests").exists()
    assert not (tmp_path / "historical").exists()
    assert not (tmp_path / "WealthMachineIntelligenceEnhanced").exists()
    return tmp_path, command, environment


@pytest.mark.parametrize("missing", ["JWT_SECRET_KEY", "JWT_ISSUER", "JWT_AUDIENCE",
                                     "WEALTHMACHINE_SIGNING_KEY"])
def test_packaged_startup_refuses_missing_config(package, missing):
    directory, command, environment = package
    environment.pop(missing)
    environment.update(ALLOW_DEMO_AUTH="true", UNIIMENTE_BRIDGE_DEV_UNSIGNED="1")
    result = subprocess.run(command, cwd=directory, env=environment,
                            capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode != 0
    assert "required" in result.stderr.lower()
    assert "Application startup failed" in result.stderr


def test_exact_packaged_command_protected_bridge(package):
    directory, command, environment = package
    # Fail visibly if the fixed packaged port is occupied; never kill its owner.
    with socket.socket() as probe:
        probe.bind(("0.0.0.0", 5000))
    with (directory / "server.log").open("w+") as log:
        process = subprocess.Popen(command, cwd=directory, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url="http://localhost:5000", trust_env=False,
                              timeout=5) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        log.seek(0)
                        pytest.fail(log.read())
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.05)
                else:
                    log.seek(0)
                    pytest.fail("Packaged server failed to become ready: " + log.read())
                body = json.dumps(fire_packet(id="synthetic-packaged-mission", schema_version='1.1')).encode()
                claims = jwt.get_unverified_claims(token())
                invalid = [None, "demo", "demo_token", "stub-token", "arbitrary-text",
                           token(exp=1), token(iss="wrong"), token(aud="wrong"),
                           jwt.encode(claims, KEY, algorithm="HS384"),
                           jwt.encode(claims, "wrong-key", algorithm="HS256")]
                for credential in invalid:
                    headers = _signed_headers(body, key=BRIDGE_KEY)
                    if credential:
                        headers["Authorization"] = f"Bearer {credential}"
                    response = client.post("/api/opportunities/intake", content=body, headers=headers)
                    assert response.status_code == 401
                # A JWT alone cannot bypass signed-body admission.
                assert client.post("/api/opportunities/intake", content=body,
                                   headers={"Authorization": f"Bearer {token()}"}).status_code == 401
                headers = _signed_headers(body, key=BRIDGE_KEY, idempotency="packaged-only")
                headers["Authorization"] = f"Bearer {token()}"
                response = client.post("/api/opportunities/intake", content=body, headers=headers)
                assert response.status_code == 200, response.text
                assessment = response.json()
                assert assessment["requires_human_approval"] is True
                assert assessment["opportunity_packet_id"] == "synthetic-packaged-mission"
                target = f"/api/ventures/{assessment['id']}/assessment"
                assert client.get(target).status_code == 401
                from src.services.bridge_security import build_headers
                import unittest.mock
                with unittest.mock.patch.dict(os.environ, {'WEALTHMACHINE_SIGNING_KEY':BRIDGE_KEY}):
                    headers = build_headers(b'', identity='daleobanks', schema_version='1.1',
                        operation='assessment.get:' + assessment['id'])
                headers['Authorization'] = f'Bearer {token()}'
                assert client.get(target, headers=headers).status_code == 200
                assert client.post("/auth/login", data={"username": "demo", "password": "demo"}).status_code == 404
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
