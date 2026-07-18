"""Domain models for the Venture Cell constitutional control plane.

The human-facing autonomy level is only a summary. Authority is represented by
short-lived grants for a specific agent, action, resource, context, and budget.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Any, Mapping, Optional


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset, tuple, list)):
        converted = [_json_safe(item) for item in value]
        if isinstance(value, (set, frozenset)):
            return sorted(converted, key=lambda item: json.dumps(item, sort_keys=True))
        return converted
    if hasattr(value, "__dataclass_fields__"):
        return _json_safe(asdict(value))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def canonical_json(value: Any) -> str:
    """Serialize a value deterministically for hashes and approval binding."""

    return json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class AutonomyStage(IntEnum):
    """Release stage for one capability, not a rank for an entire cell."""

    SIMULATE = 0
    SHADOW = 1
    SUPERVISED_CANARY = 2
    BOUNDED = 3
    SCALED_BOUNDED = 4


class RiskTier(IntEnum):
    OBSERVE = 0
    REVERSIBLE_INTERNAL = 1
    BOUNDED_EXTERNAL = 2
    MATERIAL = 3
    CONSTITUTIONAL = 4


class CellStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


class PolicyDisposition(str, Enum):
    ALLOW = "allow"
    SHADOW = "shadow"
    REVIEW = "review"
    DENY = "deny"


class IncidentSeverity(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ActionDefinition:
    action_type: str
    risk_tier: RiskTier
    minimum_stage: AutonomyStage
    required_human_approvals: int = 0
    description: str = ""


@dataclass(frozen=True)
class VentureCellCharter:
    cell_id: str
    mission: str
    owner_id: str
    allowed_geographies: frozenset[str] = field(default_factory=frozenset)
    allowed_data_classes: frozenset[str] = field(default_factory=frozenset)
    prohibited_actions: frozenset[str] = field(default_factory=frozenset)
    max_daily_spend_usd: Decimal = Decimal("0")
    max_total_spend_usd: Decimal = Decimal("0")
    kill_conditions: tuple[str, ...] = ()
    policy_version: str = "v1"
    status: CellStatus = CellStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class CapabilityGrant:
    grant_id: str
    cell_id: str
    agent_id: str
    action_type: str
    stage: AutonomyStage
    resource_prefixes: tuple[str, ...]
    expires_at: datetime
    context_fingerprint: str
    allowed_geographies: frozenset[str] = field(default_factory=frozenset)
    allowed_data_classes: frozenset[str] = field(default_factory=frozenset)
    parameter_constraints: Mapping[str, tuple[Any, ...]] = field(default_factory=dict)
    max_per_action_usd: Decimal = Decimal("0")
    max_daily_spend_usd: Decimal = Decimal("0")
    max_total_spend_usd: Decimal = Decimal("0")
    delegation_depth: int = 0
    parent_grant_id: Optional[str] = None
    created_by: str = ""
    issued_at: datetime = field(default_factory=utc_now)
    active: bool = True


@dataclass(frozen=True)
class ActionIntent:
    action_id: str
    cell_id: str
    agent_id: str
    action_type: str
    resource: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    amount_usd: Decimal = Decimal("0")
    geography: Optional[str] = None
    data_classes: frozenset[str] = field(default_factory=frozenset)
    context_fingerprint: str = ""
    requested_at: datetime = field(default_factory=utc_now)

    def fingerprint(self) -> str:
        """Bind approvals and idempotency to the consequential fields."""

        return digest(
            {
                "action_id": self.action_id,
                "cell_id": self.cell_id,
                "agent_id": self.agent_id,
                "action_type": self.action_type,
                "resource": self.resource,
                "payload": self.payload,
                "amount_usd": self.amount_usd,
                "geography": self.geography,
                "data_classes": self.data_classes,
                "context_fingerprint": self.context_fingerprint,
            }
        )


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    action_fingerprint: str
    approver_id: str
    policy_version: str
    expires_at: datetime
    approved_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class PolicyDecision:
    action_id: str
    action_type: str
    disposition: PolicyDisposition
    reason_codes: tuple[str, ...]
    policy_version: str
    risk_tier: Optional[RiskTier] = None
    grant_id: Optional[str] = None
    required_human_approvals: int = 0
    valid_human_approvals: int = 0
    evaluated_at: datetime = field(default_factory=utc_now)

    @property
    def allowed(self) -> bool:
        return self.disposition is PolicyDisposition.ALLOW


@dataclass(frozen=True)
class ExecutionReceipt:
    action_id: str
    intent_fingerprint: str
    grant_id: str
    status: str
    result_digest: str
    external_reference: Optional[str] = None
    executed_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class GatewayResult:
    decision: PolicyDecision
    receipt: Optional[ExecutionReceipt] = None
    result: Any = None


@dataclass(frozen=True)
class Incident:
    incident_id: str
    cell_id: str
    severity: IncidentSeverity
    reason: str
    actor_id: str
    grant_id: Optional[str] = None
    occurred_at: datetime = field(default_factory=utc_now)


__all__ = [
    "ActionDefinition",
    "ActionIntent",
    "ApprovalRecord",
    "AutonomyStage",
    "CapabilityGrant",
    "CellStatus",
    "ExecutionReceipt",
    "GatewayResult",
    "Incident",
    "IncidentSeverity",
    "PolicyDecision",
    "PolicyDisposition",
    "RiskTier",
    "VentureCellCharter",
    "canonical_json",
    "digest",
    "utc_now",
]
