"""Model clients for the UAT swarm.

A ModelClient turns (system prompt, task, JSON schema) into a validated
dict plus usage. ClaudeClient calls the Messages API with structured
outputs, server-side web search where the role needs it, and the default
refusal fallback. Any other provider (an xAI/Grok client, a local model)
plugs in by implementing the same `complete` method under its own lineage
name — which is what lets the swarm ledger grade cross-lineage review.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

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


class ClaudeClient:
    """Claude via the official SDK. Reads credentials from the environment."""

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
