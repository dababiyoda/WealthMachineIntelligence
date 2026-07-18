"""Configuration and lifecycle for the durable Constitutional Control Plane."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from src.control import (
    EvidenceLedger,
    ExecutionGateway,
    PolicyEngine,
    SQLiteControlStateStore,
    build_default_control_plane,
)


class ControlRuntimeConfigurationError(RuntimeError):
    """Raised when the API cannot construct a safe control-plane runtime."""


@dataclass(frozen=True)
class ControlPlaneConfig:
    root_authority_id: str
    human_authority_ids: frozenset[str]
    state_db_path: Path
    evidence_ledger_path: Path
    policy_version: str = "v1"
    max_grant_ttl_hours: int = 24
    max_approval_ttl_minutes: int = 60


@dataclass(frozen=True)
class ControlPlaneRuntime:
    config: ControlPlaneConfig
    state_store: SQLiteControlStateStore
    evidence_ledger: EvidenceLedger
    policy: PolicyEngine
    gateway: ExecutionGateway


_runtime: ControlPlaneRuntime | None = None
_runtime_lock = threading.RLock()


def _csv_identifiers(raw: str) -> frozenset[str]:
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    if len(values) != len(set(values)):
        raise ControlRuntimeConfigurationError(
            "control authority identifiers must be unique"
        )
    return frozenset(values)


def _bounded_integer(name: str, default: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ControlRuntimeConfigurationError(
            f"{name} must be an integer"
        ) from exc
    if value <= 0 or value > maximum:
        raise ControlRuntimeConfigurationError(
            f"{name} must be between 1 and {maximum}"
        )
    return value


def load_control_plane_config() -> ControlPlaneConfig:
    """Load an explicit authority map and durable local reference paths."""

    environment = os.getenv("ENVIRONMENT", "development").lower()
    root_authority_id = os.getenv("CONTROL_ROOT_AUTHORITY_ID", "").strip()
    if not root_authority_id:
        raise ControlRuntimeConfigurationError(
            "CONTROL_ROOT_AUTHORITY_ID must be explicitly configured"
        )

    configured_humans = _csv_identifiers(
        os.getenv("CONTROL_HUMAN_AUTHORITY_IDS", "")
    )
    human_authority_ids = configured_humans | {root_authority_id}
    if len(human_authority_ids) < 2:
        raise ControlRuntimeConfigurationError(
            "at least two distinct human authorities are required for dual control"
        )

    raw_state_path = os.getenv("CONTROL_STATE_DB_PATH", "").strip()
    raw_ledger_path = os.getenv("CONTROL_EVIDENCE_LEDGER_PATH", "").strip()
    if environment == "production" and (not raw_state_path or not raw_ledger_path):
        raise ControlRuntimeConfigurationError(
            "production requires explicit control state and evidence ledger paths"
        )
    state_db_path = Path(raw_state_path or "var/control/control.db")
    evidence_ledger_path = Path(
        raw_ledger_path or "var/control/evidence.jsonl"
    )
    if environment == "production" and (
        not state_db_path.is_absolute() or not evidence_ledger_path.is_absolute()
    ):
        raise ControlRuntimeConfigurationError(
            "production control state and evidence paths must be absolute"
        )
    if state_db_path.resolve() == evidence_ledger_path.resolve():
        raise ControlRuntimeConfigurationError(
            "control state and evidence ledger must use different paths"
        )

    policy_version = os.getenv("CONTROL_POLICY_VERSION", "v1").strip()
    if not policy_version:
        raise ControlRuntimeConfigurationError(
            "CONTROL_POLICY_VERSION cannot be empty"
        )

    return ControlPlaneConfig(
        root_authority_id=root_authority_id,
        human_authority_ids=human_authority_ids,
        state_db_path=state_db_path,
        evidence_ledger_path=evidence_ledger_path,
        policy_version=policy_version,
        max_grant_ttl_hours=_bounded_integer(
            "CONTROL_MAX_GRANT_TTL_HOURS",
            24,
            168,
        ),
        max_approval_ttl_minutes=_bounded_integer(
            "CONTROL_MAX_APPROVAL_TTL_MINUTES",
            60,
            1440,
        ),
    )


def build_control_plane_runtime(
    config: ControlPlaneConfig,
) -> ControlPlaneRuntime:
    """Build or reconstruct one single-process durable reference runtime."""

    state_store = SQLiteControlStateStore(config.state_db_path)
    evidence_ledger = EvidenceLedger(config.evidence_ledger_path)
    policy, gateway = build_default_control_plane(
        root_actor_id=config.root_authority_id,
        human_authorities=config.human_authority_ids,
        evidence_ledger=evidence_ledger,
        policy_version=config.policy_version,
        state_store=state_store,
    )
    if not state_store.verify_integrity():
        raise ControlRuntimeConfigurationError(
            "control state integrity verification failed"
        )
    if not evidence_ledger.verify_chain():
        raise ControlRuntimeConfigurationError(
            "evidence ledger integrity verification failed"
        )
    return ControlPlaneRuntime(
        config=config,
        state_store=state_store,
        evidence_ledger=evidence_ledger,
        policy=policy,
        gateway=gateway,
    )


def get_control_plane_runtime() -> ControlPlaneRuntime:
    """Return the process runtime, initializing it exactly once."""

    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = build_control_plane_runtime(load_control_plane_config())
        return _runtime


def initialize_production_control_plane() -> None:
    """Fail production startup when the control plane cannot be reconstructed."""

    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        get_control_plane_runtime()


def reset_control_plane_runtime() -> None:
    """Clear the process cache for isolated tests and controlled reloads."""

    global _runtime
    with _runtime_lock:
        _runtime = None


__all__ = [
    "ControlPlaneConfig",
    "ControlPlaneRuntime",
    "ControlRuntimeConfigurationError",
    "build_control_plane_runtime",
    "get_control_plane_runtime",
    "initialize_production_control_plane",
    "load_control_plane_config",
    "reset_control_plane_runtime",
]
