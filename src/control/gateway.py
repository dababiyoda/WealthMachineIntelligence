"""Single policy-enforced execution gateway for consequential actions."""

from __future__ import annotations

import threading
from dataclasses import replace
from typing import Any, Callable, Mapping, Optional

from .models import (
    ActionIntent,
    ExecutionReceipt,
    GatewayResult,
    Incident,
    IncidentSeverity,
    PolicyDecision,
    PolicyDisposition,
    RiskTier,
    digest,
)
from .policy_engine import PolicyEngine


Executor = Callable[[ActionIntent], Any]


class ExecutionGateway:
    """Authorize, execute once, and produce a tamper-evident receipt."""

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self.policy_engine = policy_engine
        self.ledger = policy_engine.ledger
        self._executors: dict[str, Executor] = {}
        self._fingerprints: dict[str, str] = {}
        self._completed: dict[str, tuple[str, GatewayResult]] = {}
        self._lock = threading.RLock()

    def register_executor(self, action_type: str, executor: Executor) -> None:
        """Install a trusted adapter during application bootstrap."""

        if action_type not in self.policy_engine.action_definitions:
            raise ValueError("cannot register an executor for an unknown action")
        self._executors[action_type] = executor

    def submit(self, intent: ActionIntent) -> GatewayResult:
        """Evaluate and, only when allowed, invoke the registered adapter once."""

        with self._lock:
            fingerprint = intent.fingerprint()
            seen_fingerprint = self._fingerprints.get(intent.action_id)
            if seen_fingerprint is not None and seen_fingerprint != fingerprint:
                conflict = PolicyDecision(
                    action_id=intent.action_id,
                    action_type=intent.action_type,
                    disposition=PolicyDisposition.DENY,
                    reason_codes=("idempotency_key_conflict",),
                    policy_version=self.policy_engine.policy_version,
                )
                self.ledger.append(
                    "gateway_denied",
                    "execution-gateway",
                    {
                        "reason": "idempotency_key_conflict",
                        "intent_fingerprint": fingerprint,
                    },
                    cell_id=intent.cell_id,
                    action_id=intent.action_id,
                )
                return GatewayResult(decision=conflict)

            previous = self._completed.get(intent.action_id)
            if previous:
                previous_fingerprint, previous_result = previous
                if previous_fingerprint == fingerprint:
                    return previous_result
            self._fingerprints[intent.action_id] = fingerprint

            self.ledger.append(
                "action_intent_received",
                intent.agent_id,
                {
                    "intent_fingerprint": fingerprint,
                    "action_type": intent.action_type,
                    "resource": intent.resource,
                    "amount_usd": intent.amount_usd,
                    "geography": intent.geography,
                    "data_classes": intent.data_classes,
                    "context_fingerprint": intent.context_fingerprint,
                    "payload_digest": digest(intent.payload),
                },
                cell_id=intent.cell_id,
                action_id=intent.action_id,
            )
            decision = self.policy_engine.evaluate(intent)
            if not decision.allowed:
                # Review, shadow, and policy-denied intents may become valid after
                # an approval, promotion, or administrative correction. The
                # fingerprint remains reserved, but no execution result is cached.
                return GatewayResult(decision=decision)

            executor = self._executors.get(intent.action_type)
            if executor is None:
                denied = replace(
                    decision,
                    disposition=PolicyDisposition.DENY,
                    reason_codes=("executor_not_registered",),
                )
                self.ledger.append(
                    "gateway_denied",
                    "execution-gateway",
                    {
                        "reason": "executor_not_registered",
                        "intent_fingerprint": fingerprint,
                        "grant_id": decision.grant_id,
                    },
                    cell_id=intent.cell_id,
                    action_id=intent.action_id,
                )
                # No adapter was invoked, so the same exact intent may be retried
                # after trusted bootstrap installs one.
                return GatewayResult(decision=denied)

            try:
                adapter_result = executor(intent)
            except Exception as exc:  # pragma: no cover - adapter-specific failures
                receipt = ExecutionReceipt(
                    action_id=intent.action_id,
                    intent_fingerprint=fingerprint,
                    grant_id=decision.grant_id or "",
                    status="failed",
                    result_digest=digest({"error_type": type(exc).__name__}),
                )
                self.ledger.append(
                    "execution_failed",
                    "execution-gateway",
                    {
                        "intent_fingerprint": fingerprint,
                        "grant_id": decision.grant_id,
                        "error_type": type(exc).__name__,
                    },
                    cell_id=intent.cell_id,
                    action_id=intent.action_id,
                )
                severity = (
                    IncidentSeverity.MAJOR
                    if decision.risk_tier is not None
                    and decision.risk_tier >= RiskTier.BOUNDED_EXTERNAL
                    else IncidentSeverity.MINOR
                )
                self.policy_engine.report_incident(
                    Incident(
                        incident_id=f"{intent.action_id}:executor-failure",
                        cell_id=intent.cell_id,
                        severity=severity,
                        reason="trusted action adapter failed",
                        actor_id="execution-gateway",
                        grant_id=decision.grant_id,
                    )
                )
                result = GatewayResult(decision=decision, receipt=receipt)
                self._completed[intent.action_id] = (fingerprint, result)
                return result

            external_reference = self._external_reference(adapter_result)
            receipt = ExecutionReceipt(
                action_id=intent.action_id,
                intent_fingerprint=fingerprint,
                grant_id=decision.grant_id or "",
                status="executed",
                result_digest=digest(adapter_result),
                external_reference=external_reference,
            )
            self.policy_engine.record_execution(intent, receipt.grant_id)
            self.ledger.append(
                "execution_succeeded",
                "execution-gateway",
                {
                    "intent_fingerprint": fingerprint,
                    "grant_id": receipt.grant_id,
                    "result_digest": receipt.result_digest,
                    "external_reference": external_reference,
                },
                cell_id=intent.cell_id,
                action_id=intent.action_id,
            )
            result = GatewayResult(
                decision=decision,
                receipt=receipt,
                result=adapter_result,
            )
            self._completed[intent.action_id] = (fingerprint, result)
            return result

    @staticmethod
    def _external_reference(result: Any) -> Optional[str]:
        if isinstance(result, Mapping):
            reference = result.get("external_reference") or result.get("id")
            return str(reference) if reference is not None else None
        return None


__all__ = ["ExecutionGateway", "Executor"]
