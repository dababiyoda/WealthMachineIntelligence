"""Single policy-enforced execution gateway for consequential actions."""

from __future__ import annotations

import threading
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional

from .execution_context import activate_authorized_execution
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
from .state_store import (
    StateIntegrityError,
    deserialize_gateway_result,
    serialize_gateway_result,
)

if TYPE_CHECKING:
    from .state_store import SQLiteControlStateStore


Executor = Callable[[ActionIntent], Any]


class ExecutionGateway:
    """Authorize, execute once, and produce a tamper-evident receipt."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        state_store: Optional["SQLiteControlStateStore"] = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.ledger = policy_engine.ledger
        self.state_store = state_store or policy_engine.state_store
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
            if self.state_store is not None:
                stored = self.state_store.reserve_action(
                    intent.action_id,
                    fingerprint,
                )
                if stored.fingerprint != fingerprint:
                    return self._deny_idempotency(
                        intent,
                        fingerprint,
                        "idempotency_key_conflict",
                    )
                if stored.lifecycle == "completed":
                    return self._recover_completed(
                        intent,
                        fingerprint,
                        stored.result_payload,
                    )
                if stored.lifecycle == "inflight":
                    return self._deny_idempotency(
                        intent,
                        fingerprint,
                        "reconciliation_required_for_inflight_action",
                    )

            seen_fingerprint = self._fingerprints.get(intent.action_id)
            if seen_fingerprint is not None and seen_fingerprint != fingerprint:
                return self._deny_idempotency(
                    intent,
                    fingerprint,
                    "idempotency_key_conflict",
                )

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

            if self.state_store is not None:
                claimed = self.state_store.mark_inflight(
                    intent.action_id,
                    fingerprint,
                )
                if not claimed:
                    current = self.state_store.load_action(intent.action_id)
                    if current is not None and current.lifecycle == "completed":
                        return self._recover_completed(
                            intent,
                            fingerprint,
                            current.result_payload,
                        )
                    return self._deny_idempotency(
                        intent,
                        fingerprint,
                        "reconciliation_required_for_inflight_action",
                    )

            try:
                with activate_authorized_execution(intent, decision):
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
                if self.state_store is not None:
                    self.state_store.complete_action(
                        intent.action_id,
                        fingerprint,
                        serialize_gateway_result(result),
                    )
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
            if self.state_store is not None:
                self.state_store.complete_action(
                    intent.action_id,
                    fingerprint,
                    serialize_gateway_result(result),
                )
            self._completed[intent.action_id] = (fingerprint, result)
            return result

    def _deny_idempotency(
        self,
        intent: ActionIntent,
        fingerprint: str,
        reason: str,
    ) -> GatewayResult:
        definition = self.policy_engine.action_definitions.get(intent.action_type)
        denied = PolicyDecision(
            action_id=intent.action_id,
            action_type=intent.action_type,
            disposition=PolicyDisposition.DENY,
            reason_codes=(reason,),
            policy_version=self.policy_engine.policy_version,
            risk_tier=definition.risk_tier if definition is not None else None,
        )
        self.ledger.append(
            "gateway_denied",
            "execution-gateway",
            {
                "reason": reason,
                "intent_fingerprint": fingerprint,
            },
            cell_id=intent.cell_id,
            action_id=intent.action_id,
        )
        return GatewayResult(decision=denied)

    def _recover_completed(
        self,
        intent: ActionIntent,
        fingerprint: str,
        payload: Mapping[str, Any] | None,
    ) -> GatewayResult:
        if payload is None:
            raise StateIntegrityError("completed gateway action has no result")
        try:
            recovered = deserialize_gateway_result(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise StateIntegrityError("stored gateway result is malformed") from exc
        receipt = recovered.receipt
        if (
            recovered.decision.action_id != intent.action_id
            or recovered.decision.action_type != intent.action_type
            or (receipt is not None and receipt.action_id != intent.action_id)
            or (
                receipt is not None
                and receipt.intent_fingerprint != fingerprint
            )
        ):
            raise StateIntegrityError("stored gateway result does not match action")
        self._fingerprints[intent.action_id] = fingerprint
        self._completed[intent.action_id] = (fingerprint, recovered)
        self.ledger.append(
            "gateway_replay_returned",
            "execution-gateway",
            {
                "intent_fingerprint": fingerprint,
                "receipt_status": receipt.status if receipt is not None else None,
            },
            cell_id=intent.cell_id,
            action_id=intent.action_id,
        )
        return recovered

    @staticmethod
    def _external_reference(result: Any) -> Optional[str]:
        if isinstance(result, Mapping):
            reference = result.get("external_reference") or result.get("id")
            return str(reference) if reference is not None else None
        return None


__all__ = ["ExecutionGateway", "Executor"]
