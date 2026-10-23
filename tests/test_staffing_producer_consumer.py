"""Real pinned producer -> packaged consumer, synthetic localhost only."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from tests.fixtures.auth import token
from tests.test_packaged_startup import build_package
from tests.test_staffing_evidence import LABEL, packet, plan

PRODUCER = """
import json, sys
from dataclasses import asdict
from datetime import datetime
from db.models import OpportunityPacket
from services.idea_refinery import stated_evidence
from services.wealthmachine_client import WealthMachineClient
payload = json.load(sys.stdin)
payload.pop('schema_version')
payload['created_at'] = datetime.fromisoformat(payload['created_at'])
original = payload['evidence'][1]
carried = stated_evidence('Staff the docks and the line. ' + original)
assert carried == [original], carried
payload['evidence'][1] = carried[0]
client = WealthMachineClient()
try:
    result = client.evaluate(OpportunityPacket(**payload))
    print('RESULT=' + json.dumps(asdict(result), default=str, sort_keys=True))
finally:
    client.close()
"""


def test_reported_figures_change_the_real_signed_producer_consumer_path(tmp_path):
    source = os.getenv("DALEOBANKS_SOURCE")
    if not source:
        pytest.skip("DALEOBANKS_SOURCE unavailable: staffing cross-repository gate NOT RUN")
    source = Path(source).resolve()
    assert (source / "services/wealthmachine_client.py").is_file()
    directory, command, environment = build_package(tmp_path)
    with socket.socket() as probe:
        # Match uvicorn's socket reuse: TIME_WAIT from the prior test is fine,
        # but an actively listening owner must still fail rather than be killed.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("0.0.0.0", 5000))
    producer_env = environment.copy()
    producer_env.update(
        WEALTHMACHINE_URL="http://localhost:5000", WEALTHMACHINE_MODE="http",
        WEALTHMACHINE_INTAKE_TOKEN=token(), PERSIST_STORE="false",
        LEDGER_PATH=str(directory / "daleo-decisions.jsonl"),
        UNIIMENTE_BRIDGE_STATE_PATH=str(directory / "daleo-bridge.jsonl"),
    )

    def produce(report, identifier):
        value = packet(report, id=identifier)
        assert value["evidence"][1].startswith(LABEL)
        result = subprocess.run(
            [sys.executable, "-c", PRODUCER], cwd=source, env=producer_env,
            input=json.dumps(value), capture_output=True, text=True, timeout=20, check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        return json.loads(next(line[7:] for line in result.stdout.splitlines() if line.startswith("RESULT=")))

    with (directory / "staffing-server.log").open("w+") as log:
        process = subprocess.Popen(command, cwd=directory, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    log.seek(0)
                    pytest.fail(log.read())
                try:
                    if httpx.get("http://localhost:5000/health", trust_env=False).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.05)
            else:
                pytest.fail("packaged staffing consumer startup timeout")
            complete = produce(plan(), "staffing-complete")
            short = produce(plan(4, 8), "staffing-short")
            assert complete["opportunity_score"] == short["opportunity_score"]
            assert complete["go_no_go"] == "go"
            assert short["go_no_go"] == "needs_more_evidence"
            assert complete["reasons"] != short["reasons"]
            assert "shortage of 4 units" in short["recommended_next_action"]
            assert complete["requires_human_approval"] is short["requires_human_approval"] is True
            assert any("unverified report" in reason for reason in short["reasons"])
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
