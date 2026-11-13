"""ClaudeClient request/response handling against a stand-in SDK (no network)."""
from types import SimpleNamespace as NS

import pytest

from src.swarm.model import ClaudeClient, ModelError


def _resp(stop, text='{"ok": true}', model="claude-opus-5-5"):
    usage = NS(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=0,
               cache_read_input_tokens=0, server_tool_use=NS(web_search_requests=2))
    return NS(stop_reason=stop, content=[NS(type="text", text=text)], model=model, usage=usage,
              stop_details=NS(category="cyber"))


class FakeSDK:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = NS(messages=NS(stream=self._stream))

    def _stream(self, **kw):
        self.requests.append(kw)
        resp = self.responses.pop(0)

        class _Ctx:
            def __enter__(self_inner):
                return NS(get_final_message=lambda: resp)

            def __exit__(self_inner, *a):
                return False
        return _Ctx()


def test_request_shape_and_cost():
    sdk = FakeSDK([_resp("end_turn")])
    out = ClaudeClient(client=sdk).complete("sys", "task", {"type": "object"}, web=True)
    req = sdk.requests[0]
    assert req["model"] == "claude-opus-5-5" and req["fallbacks"] == "default"
    assert req["betas"] == ["server-side-fallback-2026-07-01"]
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert req["tools"][0]["type"] == "web_search_20260209"
    assert "temperature" not in req and "thinking" not in req
    assert out.data == {"ok": True}
    assert out.cost_usd == pytest.approx(1000 * 4 / 1e6 + 500 * 20 / 1e6 + 0.02)


def test_pause_turn_continues():
    sdk = FakeSDK([_resp("pause_turn", text=""), _resp("end_turn")])
    assert ClaudeClient(client=sdk).complete("s", "t", {}, web=True).data == {"ok": True}
    assert sdk.requests[1]["messages"][-1]["role"] == "assistant"


@pytest.mark.parametrize("stop,match", [("refusal", "declined"), ("max_tokens", "truncated")])
def test_refusal_and_truncation_raise(stop, match):
    with pytest.raises(ModelError, match=match):
        ClaudeClient(client=FakeSDK([_resp(stop)])).complete("s", "t", {}, web=False)


def test_invalid_json_raises():
    with pytest.raises(ModelError, match="invalid JSON"):
        ClaudeClient(client=FakeSDK([_resp("end_turn", text="not json")])).complete("s", "t", {}, False)
