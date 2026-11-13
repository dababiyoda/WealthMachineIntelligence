"""Local-first model routing (Kernel INTENT-20260930-open-source-first).

LocalClient is exercised against a real loopback HTTP server speaking the
OpenAI chat protocol, so the request path is tested, not mocked. The route
is chosen by explicit setting only; a paid key never selects it.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.swarm.model import LocalClient, ModelError, ScriptedClient, client_from_env
from src.swarm.roles import SCOUT

SEEN = "https://cms.gov/revalidation"


@pytest.fixture
def server():
    replies, requests = [], []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            status, body = replies.pop(0)
            self.send_response(status)
            if status == 302:
                self.send_header("Location", "https://api.example.com/v1/chat/completions")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def log_message(self, *a):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/v1", replies, requests
    httpd.shutdown()


def _chat(content, finish="stop"):
    return 200, {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(content)}}]}


def _scout(urls):
    return {"opportunities": [{"name": "audit", "one_liner": "", "buyer": "", "recurring_paid_problem": "",
                               "edge": "", "why_now": "",
                               "evidence": [{"url": u, "claim": "c"} for u in urls]}]}


def test_completes_over_loopback_at_zero_fee(server):
    url, replies, requests = server
    replies.append(_chat(_scout([SEEN])))
    out = LocalClient(url, "qwen3.5:4b").complete("sys", f"seed: {SEEN}", SCOUT, web=True)
    assert out.cost_usd == 0.0 and out.model == "qwen3.5:4b"
    assert out.data["opportunities"][0]["evidence"][0]["url"] == SEEN
    path, body = requests[0]
    assert path == "/v1/chat/completions" and body["model"] == "qwen3.5:4b"
    assert "JSON schema" in body["messages"][0]["content"]


def test_unseen_sources_are_dropped_not_trusted(server):
    url, replies, _ = server
    replies.append(_chat(_scout([SEEN, "https://invented.example/report"])))
    out = LocalClient(url).complete("sys", f"seed: {SEEN}", SCOUT, web=True)
    assert [e["url"] for e in out.data["opportunities"][0]["evidence"]] == [SEEN]


def test_missing_fields_truncation_and_redirect_refuse(server):
    url, replies, _ = server
    client = LocalClient(url)
    replies.append(_chat({"wrong": 1}))
    with pytest.raises(ModelError, match="required"):
        client.complete("s", "t", SCOUT, web=False)
    replies.append(_chat(_scout([]), finish="length"))
    with pytest.raises(ModelError, match="truncated"):
        client.complete("s", "t", SCOUT, web=False)
    replies.append((302, {}))
    with pytest.raises(ModelError):
        client.complete("s", "t", SCOUT, web=False)


def test_server_down_is_an_error_not_a_hosted_fallback():
    with pytest.raises(ModelError, match="unavailable"):
        LocalClient("http://127.0.0.1:9/v1", timeout_seconds=2).complete("s", "t", SCOUT, web=False)


@pytest.mark.parametrize("base_url,model", [
    ("https://api.openai.com/v1", "qwen3.5:4b"),
    ("http://user:pw@127.0.0.1:11434/v1", "qwen3.5:4b"),
    ("http://127.0.0.1:11434/v2", "qwen3.5:4b"),
    ("http://127.0.0.1:11434/v1", "gpt-oss:120b-cloud"),
])
def test_hosted_or_cloud_routes_refused(base_url, model):
    with pytest.raises(ModelError):
        LocalClient(base_url, model)


def test_api_key_does_not_change_the_route(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-present")
    monkeypatch.delenv("UAT_MODEL_PROVIDER", raising=False)
    assert isinstance(client_from_env(), LocalClient)
    with pytest.raises(ModelError, match="unknown"):
        client_from_env("openai")


def test_call_ceiling_bounds_free_inference(tmp_path):
    from src.services.uat_store import UATStore
    from src.swarm.runtime import RuntimeConfig, SwarmRuntime
    from tests.test_swarm_runtime import script

    store = UATStore(str(tmp_path / "ledger.jsonl"))
    rt = SwarmRuntime(store, [ScriptedClient("local", script())],
                      RuntimeConfig(out_dir=str(tmp_path / "out"), max_model_calls=4))
    out = rt.run_cycle("c", "f")
    assert out["stopped"] and "model calls" in out["stopped"] and rt.model_calls == 4
