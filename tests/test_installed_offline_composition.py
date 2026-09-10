"""Actual packaged application and producer, with only the HTTP carrier replaced.

Runs in fresh child processes under tools/offline_test.py's inherited seccomp
boundary. This is ASGI/subprocess evidence, never Docker or TCP evidence.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests.fixtures.auth import token
from tests.test_packaged_startup import build_package


@pytest.fixture
def packaged_application(tmp_path):
    # Reuse the exact COPY composition without registering a second owner.
    return build_package(tmp_path)


SCRIPT = r'''
import hashlib, json, os, sys, urllib.error, urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import distribution
from unittest.mock import patch
from fastapi.testclient import TestClient
import adapters.bridge_transport as canonical
import events.bridge_state as durable
import adapters.contract_validation as validation
import events.spine as spine
import provenance.ledger as ledger
from src.api.main import app
from src.services import bridge_security as consumer_security
from services import bridge_security as producer_security
from services.wealthmachine_client import WealthMachineClient
from db.models import OpportunityPacket

assert producer_security.build_headers is canonical.build_headers
assert consumer_security.build_headers is canonical.build_headers
installed = distribution('uniimente-kernel-boundaries')
assert installed.version == '0.1.1'
bindings = {m.__name__: {'path': m.__file__,
    'sha256': hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()}
    for m in (canonical, durable, validation, spine, ledger)}
assert all(Path(item['path']).resolve() == Path(installed.locate_file(
    name.replace('.', '/') + '.py')).resolve() for name, item in bindings.items()), bindings

packet = OpportunityPacket(id='offline-installed-operation', source='synthetic-fixture',
    observed_pain='Evidence collection is fragmented', audience='internal research',
    evidence=['retained synthetic observation'], possible_offer='read-only analysis',
    monetization_paths=['internal efficiency'],
    created_at=datetime(2026, 9, 8, tzinfo=timezone.utc))
class Response:
    def __init__(self, response):
        self.headers, self.raw = dict(response.headers), response.content
    def read(self): return self.raw
    def __enter__(self): return self
    def __exit__(self, *exc): return False

requests = []
with TestClient(app, base_url='http://localhost') as http:
    def exchange(opener, request, timeout=None):
        # The exact serialized bytes and original headers enter real middleware,
        # JWT verification, HMAC verification, schema, evaluator and persistence.
        requests.append({'body': request.data.decode(), 'headers': dict(request.header_items())})
        response = http.request(request.get_method(), request.full_url,
                                content=request.data, headers=dict(request.header_items()))
        if response.status_code >= 400:
            raise urllib.error.HTTPError(request.full_url, response.status_code,
                                         response.text, response.headers, None)
        return Response(response)
    with patch.dict(os.environ, {'UNIIMENTE_BRIDGE_STATE_PATH': str(Path('producer.jsonl').resolve())}):
        producer = WealthMachineClient()
        producer._durable_state()  # Bind the producer's own real durable writer before exchange.
    try:
        with patch.object(urllib.request.OpenerDirector, 'open', exchange):
            result = producer.evaluate(packet)
    finally:
        producer.close()
    # No transport replay can become a second logical acceptance.
    original = requests[0]
    assert http.post('/api/opportunities/intake', content=original['body'],
                     headers=original['headers']).status_code == 401
    evidence = json.dumps({'result': asdict(result), 'bindings': bindings,
                           'request_count': len(requests)}, default=str, sort_keys=True)
    if sys.argv[1] == 'interrupt':
        print('EVIDENCE=' + evidence, flush=True)
        os._exit(75)  # Accepted result retained; consumer lifespan has not shut down.
print('EVIDENCE=' + evidence)
'''


def test_installed_real_composition_retains_result_across_processes(packaged_application):
    source = os.getenv('DALEOBANKS_SOURCE')
    if not source:
        pytest.fail('DALEOBANKS_SOURCE required for this installed composition gate')
    source = Path(source).resolve()
    directory, _, environment = packaged_application
    # Keep producer modules outside the packaged consumer; no test stubs on path.
    environment['PYTHONPATH'] = os.pathsep.join((str(source), environment.get('PYTHONPATH', '')))
    environment.update(WEALTHMACHINE_URL='http://localhost', WEALTHMACHINE_MODE='http',
        WEALTHMACHINE_INTAKE_TOKEN=token(), PERSIST_STORE='false',
        LEDGER_PATH=str(directory / 'producer-decisions.jsonl'))
    # Both processes need their own writer; never share a ledger file across owners.
    environment['UNIIMENTE_BRIDGE_STATE_PATH'] = str(directory / 'consumer.jsonl')
    evidence = []
    for mode in ('interrupt', 'normal', 'normal'):
        process = subprocess.run([sys.executable, '-u', '-c', SCRIPT, mode],
            cwd=directory, env=environment, capture_output=True, text=True, timeout=30)
        assert process.returncode == (75 if mode == 'interrupt' else 0), process.stdout + process.stderr
        evidence.append(json.loads(next(line[9:] for line in process.stdout.splitlines()
                                        if line.startswith('EVIDENCE='))))
    assert evidence[0]['result'] == evidence[1]['result'] == evidence[2]['result']
    assert evidence[0]['result']['cases']
    assert evidence[0]['result']['requires_human_approval'] is True
    assert all(item['request_count'] == 1 for item in evidence)
    assert all(item['bindings'] == evidence[0]['bindings'] for item in evidence)
    records = [json.loads(line) for line in (directory / 'consumer.jsonl').read_text().splitlines()]
    completed = [r for r in records if r['payload'].get('type') == 'bridge.operation.completed']
    assert len(completed) == 1
    print('INSTALLED_BINDINGS=' + json.dumps(evidence[0]['bindings'], sort_keys=True))
