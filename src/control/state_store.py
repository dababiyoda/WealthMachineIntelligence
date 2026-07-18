"""Durable SQLite state for policy snapshots and gateway idempotency.

SQLite is the capital-light reference store for a single control-plane process.
It provides transactional local durability and fail-closed restart behavior. It
does not replace a replicated production database, external ledger anchoring,
or atomic transactions with downstream side effects.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .models import (
    ExecutionReceipt,
    GatewayResult,
    PolicyDecision,
    PolicyDisposition,
    RiskTier,
    canonical_json,
    digest,
)


SCHEMA_VERSION = 1


class StateIntegrityError(RuntimeError):
    """Raised when durable control state fails an integrity check."""


@dataclass(frozen=True)
class StoredAction:
    action_id: str
    fingerprint: str
    lifecycle: str
    result_payload: Mapping[str, Any] | None
    was_created: bool = False


class SQLiteControlStateStore:
    """Transactional local store for restart-safe control-plane state."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS control_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS policy_snapshot (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    revision INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gateway_actions (
                    action_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    lifecycle TEXT NOT NULL,
                    result_payload TEXT,
                    record_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            existing = connection.execute(
                "SELECT value FROM control_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO control_metadata(key, value) VALUES('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            else:
                try:
                    stored_version = int(existing["value"])
                except (TypeError, ValueError) as exc:
                    raise StateIntegrityError(
                        "invalid control state schema version"
                    ) from exc
                if stored_version != SCHEMA_VERSION:
                    raise StateIntegrityError(
                        "unsupported control state schema version"
                    )

    def save_policy_state(self, payload: Mapping[str, Any]) -> int:
        serialized = canonical_json(payload)
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT revision, payload, payload_hash
                FROM policy_snapshot WHERE singleton = 1
                """
            ).fetchone()
            if row is not None:
                self._decode_policy_payload(
                    int(row["revision"]),
                    row["payload"],
                    row["payload_hash"],
                )
            revision = int(row["revision"]) + 1 if row else 1
            parsed_payload = json.loads(serialized)
            payload_hash = digest(
                {"revision": revision, "payload": parsed_payload}
            )
            connection.execute(
                """
                INSERT INTO policy_snapshot(
                    singleton, revision, payload, payload_hash, updated_at
                ) VALUES(1, ?, ?, ?, ?)
                ON CONFLICT(singleton) DO UPDATE SET
                    revision = excluded.revision,
                    payload = excluded.payload,
                    payload_hash = excluded.payload_hash,
                    updated_at = excluded.updated_at
                """,
                (revision, serialized, payload_hash, updated_at),
            )
            connection.commit()
            return revision

    def load_policy_state(self) -> Mapping[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT revision, payload, payload_hash
                FROM policy_snapshot WHERE singleton = 1
                """
            ).fetchone()
        if row is None:
            return None
        return self._decode_policy_payload(
            int(row["revision"]),
            row["payload"],
            row["payload_hash"],
        )

    @staticmethod
    def _decode_policy_payload(
        revision: int,
        serialized: str,
        payload_hash: str,
    ) -> Mapping[str, Any]:
        if revision < 1:
            raise StateIntegrityError("policy snapshot revision is invalid")
        try:
            payload = json.loads(serialized)
        except json.JSONDecodeError as exc:
            raise StateIntegrityError("policy snapshot is not valid JSON") from exc
        if not isinstance(payload, Mapping):
            raise StateIntegrityError("policy snapshot payload is not an object")
        if digest({"revision": revision, "payload": payload}) != payload_hash:
            raise StateIntegrityError("policy snapshot integrity check failed")
        return payload

    def reserve_action(self, action_id: str, fingerprint: str) -> StoredAction:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM gateway_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is not None:
                stored = self._decode_action(row)
                connection.commit()
                return stored

            updated_at = datetime.now(timezone.utc).isoformat()
            record_hash = self._action_hash(
                action_id,
                fingerprint,
                "reserved",
                None,
            )
            connection.execute(
                """
                INSERT INTO gateway_actions(
                    action_id, fingerprint, lifecycle, result_payload,
                    record_hash, updated_at
                ) VALUES(?, ?, 'reserved', NULL, ?, ?)
                """,
                (action_id, fingerprint, record_hash, updated_at),
            )
            connection.commit()
            return StoredAction(
                action_id=action_id,
                fingerprint=fingerprint,
                lifecycle="reserved",
                result_payload=None,
                was_created=True,
            )

    def mark_inflight(self, action_id: str, fingerprint: str) -> bool:
        """Atomically claim a reserved action for execution.

        Returning ``False`` means another gateway already claimed or completed
        the action. Callers must reload the record and must not invoke the
        downstream adapter.
        """

        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM gateway_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise StateIntegrityError("gateway action reservation is missing")
            stored = self._decode_action(row)
            if stored.fingerprint != fingerprint:
                connection.rollback()
                raise StateIntegrityError("gateway action fingerprint changed")
            if stored.lifecycle != "reserved":
                connection.commit()
                return False

            record_hash = self._action_hash(
                action_id,
                fingerprint,
                "inflight",
                None,
            )
            connection.execute(
                """
                UPDATE gateway_actions
                SET lifecycle = 'inflight', result_payload = NULL,
                    record_hash = ?, updated_at = ?
                WHERE action_id = ?
                """,
                (
                    record_hash,
                    datetime.now(timezone.utc).isoformat(),
                    action_id,
                ),
            )
            connection.commit()
            return True

    def complete_action(
        self,
        action_id: str,
        fingerprint: str,
        result_payload: Mapping[str, Any],
    ) -> None:
        self._transition_action(
            action_id,
            fingerprint,
            expected_lifecycles={"inflight"},
            lifecycle="completed",
            result_payload=result_payload,
        )

    def load_action(self, action_id: str) -> StoredAction | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM gateway_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return self._decode_action(row) if row is not None else None

    def verify_integrity(self) -> bool:
        try:
            self.load_policy_state()
            with self._lock, self._connect() as connection:
                rows = connection.execute("SELECT * FROM gateway_actions").fetchall()
            for row in rows:
                self._decode_action(row)
            return True
        except (StateIntegrityError, ValueError, json.JSONDecodeError):
            return False

    def _transition_action(
        self,
        action_id: str,
        fingerprint: str,
        *,
        expected_lifecycles: set[str],
        lifecycle: str,
        result_payload: Mapping[str, Any] | None,
    ) -> None:
        serialized_result = (
            canonical_json(result_payload) if result_payload is not None else None
        )
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM gateway_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise StateIntegrityError("gateway action reservation is missing")
            stored = self._decode_action(row)
            if stored.fingerprint != fingerprint:
                connection.rollback()
                raise StateIntegrityError("gateway action fingerprint changed")
            if stored.lifecycle not in expected_lifecycles:
                connection.rollback()
                raise StateIntegrityError(
                    f"invalid gateway lifecycle transition from {stored.lifecycle}"
                )
            parsed_result = (
                json.loads(serialized_result) if serialized_result is not None else None
            )
            record_hash = self._action_hash(
                action_id,
                fingerprint,
                lifecycle,
                parsed_result,
            )
            connection.execute(
                """
                UPDATE gateway_actions
                SET lifecycle = ?, result_payload = ?, record_hash = ?, updated_at = ?
                WHERE action_id = ?
                """,
                (
                    lifecycle,
                    serialized_result,
                    record_hash,
                    datetime.now(timezone.utc).isoformat(),
                    action_id,
                ),
            )
            connection.commit()

    def _decode_action(self, row: sqlite3.Row) -> StoredAction:
        lifecycle = row["lifecycle"]
        if lifecycle not in {"reserved", "inflight", "completed"}:
            raise StateIntegrityError("unknown gateway action lifecycle")
        try:
            result_payload = (
                json.loads(row["result_payload"])
                if row["result_payload"] is not None
                else None
            )
        except json.JSONDecodeError as exc:
            raise StateIntegrityError("gateway result is not valid JSON") from exc
        if result_payload is not None and not isinstance(result_payload, Mapping):
            raise StateIntegrityError("gateway result payload is not an object")
        if lifecycle == "completed" and result_payload is None:
            raise StateIntegrityError("completed gateway action has no result")
        if lifecycle != "completed" and result_payload is not None:
            raise StateIntegrityError("unfinished gateway action has a result")
        expected_hash = self._action_hash(
            row["action_id"],
            row["fingerprint"],
            lifecycle,
            result_payload,
        )
        if expected_hash != row["record_hash"]:
            raise StateIntegrityError("gateway action integrity check failed")
        return StoredAction(
            action_id=row["action_id"],
            fingerprint=row["fingerprint"],
            lifecycle=lifecycle,
            result_payload=result_payload,
        )

    @staticmethod
    def _action_hash(
        action_id: str,
        fingerprint: str,
        lifecycle: str,
        result_payload: Mapping[str, Any] | None,
    ) -> str:
        return digest(
            {
                "action_id": action_id,
                "fingerprint": fingerprint,
                "lifecycle": lifecycle,
                "result_payload": result_payload,
            }
        )


def serialize_gateway_result(result: GatewayResult) -> Mapping[str, Any]:
    decision = result.decision
    receipt = result.receipt
    return {
        "decision": {
            "action_id": decision.action_id,
            "action_type": decision.action_type,
            "disposition": decision.disposition.value,
            "reason_codes": list(decision.reason_codes),
            "policy_version": decision.policy_version,
            "risk_tier": int(decision.risk_tier) if decision.risk_tier is not None else None,
            "grant_id": decision.grant_id,
            "required_human_approvals": decision.required_human_approvals,
            "valid_human_approvals": decision.valid_human_approvals,
            "evaluated_at": decision.evaluated_at.isoformat(),
        },
        "receipt": (
            {
                "action_id": receipt.action_id,
                "intent_fingerprint": receipt.intent_fingerprint,
                "grant_id": receipt.grant_id,
                "status": receipt.status,
                "result_digest": receipt.result_digest,
                "external_reference": receipt.external_reference,
                "executed_at": receipt.executed_at.isoformat(),
            }
            if receipt is not None
            else None
        ),
        "result": normalize_gateway_result_value(result.result),
    }


def normalize_gateway_result_value(value: Any) -> Any:
    """Return the canonical JSON representation exposed by the gateway.

    Trusted adapters may use richer Python values internally. The gateway API
    intentionally returns a process-independent JSON value on the first call
    and every replay so callers never observe restart-dependent result types.
    """

    return json.loads(canonical_json(value))


def deserialize_gateway_result(payload: Mapping[str, Any]) -> GatewayResult:
    decision_payload = payload["decision"]
    receipt_payload = payload.get("receipt")
    risk_tier = decision_payload.get("risk_tier")
    decision = PolicyDecision(
        action_id=decision_payload["action_id"],
        action_type=decision_payload["action_type"],
        disposition=PolicyDisposition(decision_payload["disposition"]),
        reason_codes=tuple(decision_payload["reason_codes"]),
        policy_version=decision_payload["policy_version"],
        risk_tier=RiskTier(risk_tier) if risk_tier is not None else None,
        grant_id=decision_payload.get("grant_id"),
        required_human_approvals=int(
            decision_payload.get("required_human_approvals", 0)
        ),
        valid_human_approvals=int(decision_payload.get("valid_human_approvals", 0)),
        evaluated_at=datetime.fromisoformat(decision_payload["evaluated_at"]),
    )
    receipt = (
        ExecutionReceipt(
            action_id=receipt_payload["action_id"],
            intent_fingerprint=receipt_payload["intent_fingerprint"],
            grant_id=receipt_payload["grant_id"],
            status=receipt_payload["status"],
            result_digest=receipt_payload["result_digest"],
            external_reference=receipt_payload.get("external_reference"),
            executed_at=datetime.fromisoformat(receipt_payload["executed_at"]),
        )
        if receipt_payload is not None
        else None
    )
    return GatewayResult(
        decision=decision,
        receipt=receipt,
        result=payload.get("result"),
    )


__all__ = [
    "SCHEMA_VERSION",
    "SQLiteControlStateStore",
    "StateIntegrityError",
    "StoredAction",
    "deserialize_gateway_result",
    "normalize_gateway_result_value",
    "serialize_gateway_result",
]
