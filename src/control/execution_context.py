"""Runtime proof that a side effect is executing inside the gateway.

This is a defense-in-depth boundary for the current single-process prototype.
It prevents accidental or ordinary direct calls to trusted mutation adapters.
It is not a substitute for process isolation, brokered credentials, or network
policy in production.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterable, Iterator

from .models import ActionIntent, PolicyDecision


class UnmediatedSideEffectError(PermissionError):
    """Raised when mutation code runs without an allowed gateway decision."""


@dataclass(frozen=True)
class AuthorizedExecution:
    intent: ActionIntent
    decision: PolicyDecision


_ACTIVE_EXECUTION: ContextVar[AuthorizedExecution | None] = ContextVar(
    "venture_cell_authorized_execution",
    default=None,
)


@contextmanager
def activate_authorized_execution(
    intent: ActionIntent,
    decision: PolicyDecision,
) -> Iterator[AuthorizedExecution]:
    """Bind one allowed intent to the trusted adapter call stack."""

    if not decision.allowed or decision.action_id != intent.action_id:
        raise UnmediatedSideEffectError("only an allowed decision can activate execution")
    active = AuthorizedExecution(intent=intent, decision=decision)
    token = _ACTIVE_EXECUTION.set(active)
    try:
        yield active
    finally:
        _ACTIVE_EXECUTION.reset(token)


def require_authorized_execution(
    *,
    action_types: Iterable[str],
    resource: str | None = None,
) -> AuthorizedExecution:
    """Require an active allowed intent matching action and optional resource."""

    active = _ACTIVE_EXECUTION.get()
    if active is None or not active.decision.allowed:
        raise UnmediatedSideEffectError(
            "consequential mutation must execute through ExecutionGateway"
        )
    allowed_types = frozenset(action_types)
    if active.intent.action_type not in allowed_types:
        raise UnmediatedSideEffectError("active intent does not authorize this mutation")
    if resource is not None and active.intent.resource != resource:
        raise UnmediatedSideEffectError("active intent does not authorize this resource")
    return active


__all__ = [
    "AuthorizedExecution",
    "UnmediatedSideEffectError",
    "activate_authorized_execution",
    "require_authorized_execution",
]
