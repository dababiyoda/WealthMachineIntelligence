"""Pinned real DALEOBANKS producer against WMI's packaged composition.

Synthetic localhost only. No route, JWT, evaluation or persistence overrides.
Set DALEOBANKS_SOURCE to the reviewed consumer worktree; absence is a SKIP,
not compatibility evidence. Container execution remains a separate gate.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest

from adapters.bridge_transport import build_headers, H_SIGNATURE, H_PROTOCOL
from tests.fixtures.auth import token, BRIDGE_KEY
from tests.test_opportunity_intake import fire_packet
from tests.test_packaged_startup import package

PRODUCER = """
import json
from dataclasses import asdict
from datetime import datetime, timezone
from db.models import OpportunityPacket
from services.wealthmachine_client import WealthMachineClient
packet = OpportunityPacket(id='retained-operation', source='synthetic-fixture',
    observed_pain='Evidence collection is fragmented', audience='internal research',
    evidence=['retained synthetic observation'], possible_offer='read-only analysis',
    monetization_paths=['internal efficiency'],
    created_at=datetime(2026, 9, 8, tzinfo=timezone.utc))
client = WealthMachineClient()
try:
    result = client.evaluate(packet)
    print('RESULT=' + json.dumps(asdict(result), default=str, sort_keys=True))
finally:
    client.close()
"""


def test_real_producer_consumer_restart_and_negative_controls(package, monkeypatch):
    source = os.getenv('DALEOBANKS_SOURCE')
    if not source:
        pytest.skip('DALEOBANKS_SOURCE unavailable: cross-repository gate NOT RUN')
    source = Path(source).resolve()
    assert (source / 'services/wealthmachine_client.py').is_file()
    directory, command, environment = package
    monkeypatch.setenv('WEALTHMACHINE_SIGNING_KEY', BRIDGE_KEY)
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', 5000))
    producer_env = environment.copy()
    producer_env.update(WEALTHMACHINE_URL='http://localhost:5000',
        WEALTHMACHINE_MODE='http', WEALTHMACHINE_INTAKE_TOKEN=token(),
        PERSIST_STORE='false', LEDGER_PATH=str(directory / 'daleo-decisions.jsonl'),
        UNIIMENTE_BRIDGE_STATE_PATH=str(directory / 'daleo-bridge.jsonl'))

    def produce():
        proc = subprocess.run([sys.executable, '-c', PRODUCER], cwd=source,
            env=producer_env, capture_output=True, text=True, timeout=20)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        return json.loads(next(x[7:] for x in proc.stdout.splitlines() if x.startswith('RESULT=')))

    logs = []
    def start():
        log = (directory / f'server-{len(logs)}.log').open('w+')
        logs.append(log)
        process = subprocess.Popen(command, cwd=directory, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
        for _ in range(100):
            if process.poll() is not None:
                log.seek(0)
                pytest.fail(log.read())
            try:
                if httpx.get('http://localhost:5000/health', trust_env=False).status_code == 200:
                    return process
            except httpx.TransportError:
                pass
            time.sleep(.05)
        process.kill()
        process.wait()
        pytest.fail('packaged consumer startup timeout')

    process = start()
    try:
        first = produce()
        second = produce()  # a NEW producer process and transport nonce
        assert first == second, 'logical retry must retain id, observation time and dissent'
        assert first['cases'] and first['requires_human_approval'] is True
        body = json.dumps(fire_packet(id='negative-controls', schema_version='1.1')).encode()
        def headers(credential=None, **kw):
            h = build_headers(body, identity='daleobanks', schema_version='1.1',
                              idempotency_key='negative-controls', **kw)
            h['Authorization'] = 'Bearer ' + (credential or token())
            return h
        with httpx.Client(base_url='http://localhost:5000', trust_env=False, timeout=10) as client:
            path = '/api/opportunities/intake'
            for credential in ('demo', 'arbitrary-text', token(exp=1),
                               token(aud='wrong'), token(iss='wrong'), token(sub='wealthmachine')):
                assert client.post(path, content=body, headers=headers(credential)).status_code == 401
            h = headers()
            h.pop('Authorization')
            assert client.post(path, content=body, headers=h).status_code == 401
            h = headers()
            h.pop(H_SIGNATURE)
            assert client.post(path, content=body, headers=h).status_code == 401
            h = headers()
            h[H_PROTOCOL] = '1'
            assert client.post(path, content=body, headers=h).status_code == 401
            assert client.post(path, content=body + b' ', headers=headers()).status_code == 401
            assert client.post(path, content=body, headers=headers(recipient='kernel')).status_code == 401
            replay = headers()
            accepted = client.post(path, content=body, headers=replay)
            assert accepted.status_code == 200, accepted.text
            assert client.post(path, content=body, headers=replay).status_code == 401
            changed = json.loads(body)
            changed['observed_pain'] = 'different logical payload'
            changed = json.dumps(changed).encode()
            h = build_headers(changed, identity='daleobanks', schema_version='1.1',
                              idempotency_key='negative-controls')
            h['Authorization'] = 'Bearer ' + token()
            assert client.post(path, content=changed, headers=h).status_code == 409
            for payload in (
                {**json.loads(body), 'schema_version': '99.0'},
                {**json.loads(body), 'evidence': [{'fabricated': 'nested object'}]},
                {**json.loads(body), 'permission': 'self-minted'},
            ):
                raw = json.dumps(payload).encode()
                h = build_headers(raw, identity='daleobanks', schema_version='1.1')
                h['Authorization'] = 'Bearer ' + token()
                assert client.post(path, content=raw, headers=h).status_code in (400, 422)
        # Deliberate abrupt process interruption, not just constructing a new object.
        process.kill()
        process.wait(timeout=5)
        process = start()
        assert produce() == first
        with httpx.Client(base_url='http://localhost:5000', trust_env=False) as client:
            assert client.post('/api/opportunities/intake', content=body, headers=replay).status_code == 401
        records = [json.loads(line) for line in (directory / 'bridge.jsonl').read_text().splitlines()]
        completions = [r for r in records if r['payload'].get('type') == 'bridge.operation.completed']
        assert len(completions) == 2, 'one retained completion per logical operation, despite restart/retry'
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        for log in logs:
            log.close()
