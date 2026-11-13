"""Model clients for the UAT swarm.

A ModelClient turns (system prompt, task, JSON schema) into a validated
dict plus usage. Any provider plugs in by implementing the same `complete`
method under its own lineage name, which is what lets the swarm ledger
grade cross-lineage review.

Routing follows the Kernel open-source-first intent
(INTENT-20260930-open-source-first): the default is LocalClient, a
loopback OpenAI-protocol server (Ollama, llama.cpp, vLLM or LocalAI).
ClaudeClient is an explicit, paid opt-in (`UAT_MODEL_PROVIDER=anthropic`);
an API key in the environment never changes the route, and a local
failure never falls back to a hosted provider.
"""

from __future__ import annotations

import ipaddress
import json
import math
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlsplit

# USD per million tokens (input, output); used only for budget enforcement.
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00),
          "claude-haiku-5-5": (0.10, 0.50)}
WEB_SEARCH_COST_USD = 0.01           # per search request (estimate; verify on your invoice)


class ModelError(RuntimeError):
    """A stage could not produce a valid result (refusal, truncation, bad JSON)."""


@dataclass
class Completion:
    data: dict
    cost_usd: float
    model: str
    raw_usage: dict = field(default_factory=dict)


class ModelClient(Protocol):
    lineage: str

    def complete(self, system: str, task: str, schema: dict, web: bool) -> Completion: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ModelError("local inference redirects are refused")


def _urls_in(node) -> list:
    """Every evidence URL a result cites, wherever it sits."""
    if isinstance(node, dict):
        found = [v for k, v in node.items() if k in ("url", "source_url") and isinstance(v, str) and v]
        return found + [u for v in node.values() for u in _urls_in(v)]
    if isinstance(node, list):
        return [u for v in node for u in _urls_in(v)]
    return []


def _drop_unseen_sources(node, seen: str):
    """Remove cited sources the model could not have read: it has no web access."""
    if isinstance(node, dict):
        return {k: ("" if k in ("url", "source_url") and isinstance(v, str) and v not in seen
                    else _drop_unseen_sources(v, seen)) for k, v in node.items()}
    if isinstance(node, list):
        kept = [v for v in node
                if not (isinstance(v, dict) and isinstance(v.get("url"), str) and v["url"]
                        and v["url"] not in seen)]
        return [_drop_unseen_sources(v, seen) for v in kept]
    return node


class LocalClient:
    """A loopback OpenAI-protocol model server. Same guards as the Kernel's
    egregore/local_model.py: loopback /v1 only, no credentials, no cloud model
    tags, no proxy, no redirects, bounded input and output, no hosted fallback.

    It has no web access, so on research stages any cited URL that does not
    appear in the task is removed rather than trusted; the governor's
    two-source rule then kills an idea the model could not actually verify.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:11434/v1", model: str = "qwen3.5:4b",
                 timeout_seconds: float = 300.0, max_tokens: int = 8192, opener=None) -> None:
        url = urlsplit(base_url)
        try:
            local = url.hostname == "localhost" or ipaddress.ip_address(url.hostname or "").is_loopback
        except ValueError:
            local = False
        if (not local or url.scheme not in ("http", "https") or url.username or url.password
                or url.query or url.fragment or url.path.rstrip("/") != "/v1"):
            raise ModelError("local inference requires a loopback /v1 URL without credentials")
        if not model.strip() or "cloud" in model.lower():
            raise ModelError("a non-cloud local model name is required")
        if not (math.isfinite(timeout_seconds) and 0 < timeout_seconds <= 600):
            raise ModelError("timeout_seconds must be finite and in (0, 600]")
        if not 1 <= max_tokens <= 32768:
            raise ModelError("max_tokens must be between 1 and 32768")
        self.lineage = "local"
        self.base_url, self.model = base_url.rstrip("/"), model
        self.timeout_seconds, self.max_tokens = timeout_seconds, max_tokens
        # Loopback stays on this machine even when the worker has an HTTP proxy.
        self._opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                                             _NoRedirect())

    @classmethod
    def from_env(cls) -> LocalClient:
        return cls(base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
                   model=os.getenv("LLM_MODEL", "qwen3.5:4b"),
                   timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "300")),
                   max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8192")))

    def complete(self, system: str, task: str, schema: dict, web: bool) -> Completion:
        system = (f"{system}\n\nYou have no web access. Cite only URLs that appear in the task; "
                  "if none apply, return empty evidence lists. Reply with one JSON object matching "
                  f"this JSON schema exactly:\n{json.dumps(schema, separators=(',', ':'))}")
        payload = json.dumps({
            "model": self.model, "temperature": 0.2, "max_tokens": self.max_tokens, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": task}],
            "response_format": {"type": "json_object"},
        }).encode()
        if len(payload) > 512 * 1024:
            raise ModelError("local model input exceeds 512 KiB")
        request = urllib.request.Request(self.base_url + "/chat/completions", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                body = response.read(2 * 1024 * 1024 + 1)
        except OSError as exc:
            raise ModelError(f"local model server unavailable: {exc}") from exc
        if len(body) > 2 * 1024 * 1024:
            raise ModelError("local model response exceeds 2 MiB")
        try:
            reply = json.loads(body)["choices"][0]
            if reply.get("finish_reason") == "length":
                raise ModelError("output truncated at max_tokens")
            data = json.loads(reply["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelError(f"invalid local model completion: {exc}") from exc
        missing = [k for k in schema.get("required", []) if not isinstance(data, dict) or k not in data]
        if missing:
            raise ModelError(f"local model omitted required fields: {missing}")
        return Completion(_drop_unseen_sources(data, task), 0.0, self.model)


class ClaudeClient:
    """Claude via the official SDK: a paid provider, used only when chosen
    explicitly. Reads credentials from the environment."""

    def __init__(self, model: str = "claude-opus-5-5", effort: str = "high",
                 max_web_searches: int = 5, client=None) -> None:
        self.lineage = "claude"
        self.model = model
        self.effort = effort
        self.max_web_searches = max_web_searches
        if client is None:
            import anthropic                              # imported lazily: optional dependency
            client = anthropic.Anthropic()
        self.client = client

    def complete(self, system: str, task: str, schema: dict, web: bool) -> Completion:
        tools = ([{"type": "web_search_20260209", "name": "web_search",
                   "max_uses": self.max_web_searches}] if web else [])
        messages: list = [{"role": "user", "content": task}]
        cost, usage = 0.0, {}
        for _ in range(6):                                # bounded pause_turn continuation
            with self.client.beta.messages.stream(
                model=self.model, max_tokens=64000, system=system, messages=messages,
                tools=tools, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                output_config={"effort": self.effort,
                               "format": {"type": "json_schema", "schema": schema}},
            ) as stream:
                response = stream.get_final_message()
            cost += self._cost(response)
            usage = response.usage.to_dict() if hasattr(response.usage, "to_dict") else {}
            if response.stop_reason == "pause_turn":
                messages = messages + [{"role": "assistant", "content": response.content}]
                continue
            if response.stop_reason == "refusal":
                category = getattr(response.stop_details, "category", None)
                raise ModelError(f"model declined (category={category})")
            if response.stop_reason == "max_tokens":
                raise ModelError("output truncated at max_tokens")
            text = next((b.text for b in reversed(response.content) if b.type == "text"), "")
            try:
                return Completion(json.loads(text), cost, response.model, usage)
            except json.JSONDecodeError as exc:
                raise ModelError(f"invalid JSON from model: {exc}") from exc
        raise ModelError("too many pause_turn continuations")

    def _cost(self, response) -> float:
        p_in, p_out = PRICES.get(response.model, PRICES["claude-opus-5-5"])
        u = response.usage
        tokens_in = (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        cost = tokens_in * p_in / 1e6 + (u.output_tokens or 0) * p_out / 1e6
        cost += (getattr(u, "cache_read_input_tokens", 0) or 0) * p_in * 0.1 / 1e6
        searches = getattr(getattr(u, "server_tool_use", None), "web_search_requests", 0) or 0
        return cost + searches * WEB_SEARCH_COST_USD


def client_from_env(provider: str | None = None, model: str | None = None) -> ModelClient:
    """Pick the model route from an explicit setting, never from a key's presence."""
    provider = (provider or os.getenv("UAT_MODEL_PROVIDER", "local")).strip().lower()
    if provider == "local":
        client = LocalClient.from_env()
        if model:
            client = LocalClient(client.base_url, model, client.timeout_seconds, client.max_tokens)
        return client
    if provider == "anthropic":
        return ClaudeClient(model=model or "claude-opus-5-5")
    raise ModelError(f"unknown UAT_MODEL_PROVIDER {provider!r}; use 'local' or 'anthropic'")


class ScriptedClient:
    """Deterministic client for tests and dry runs: returns canned results per role."""

    def __init__(self, lineage: str, script, cost_usd: float = 0.0) -> None:
        self.lineage = lineage
        self.script = script                  # callable(system, task) -> dict, or raises ModelError
        self.cost_usd = cost_usd
        self.calls: list[str] = []

    def complete(self, system: str, task: str, schema: dict, web: bool) -> Completion:
        self.calls.append(system.split("ROLE: ", 1)[-1].split(" ", 1)[0])
        return Completion(self.script(system, task), self.cost_usd, f"scripted-{self.lineage}")
