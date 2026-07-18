"""Domain models for governed autonomous venture cells."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentScope(str, Enum):
    """Authority level assigned to an agent."""

    VENTURE_EXECUTIVE = "venture_executive"
    DEPARTMENT = "department"
    WORKER = "worker"


class ActionRisk(str, Enum):
    """Risk classification used by the approval policy."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    IRREVERSIBLE = "irreversible"


class VentureCellStatus(str, Enum):
    """Lifecycle state of an isolated venture organization."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


@dataclass(frozen=True)
class ApprovalPolicy:
    """Defines what a venture cell may execute without human approval."""

    autonomous_risk_levels: tuple[ActionRisk, ...] = (ActionRisk.LOW,)
    max_worker_agents_per_department: int = 5
    max_monthly_spend: float = 0.0
    allow_external_publication: bool = False
    allow_contract_execution: bool = False
    allow_money_movement: bool = False

    def requires_approval(self, risk: ActionRisk) -> bool:
        return risk not in self.autonomous_risk_levels

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["autonomous_risk_levels"] = [level.value for level in self.autonomous_risk_levels]
        return data


@dataclass(frozen=True)
class AgentBlueprint:
    """Immutable role specification used to provision a child agent."""

    role: str
    objective: str
    scope: AgentScope
    capabilities: tuple[str, ...] = ()
    reports_to: Optional[str] = None
    can_spawn_workers: bool = False

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("Agent role cannot be empty")
        if not self.objective.strip():
            raise ValueError("Agent objective cannot be empty")
        if self.scope is AgentScope.WORKER and self.can_spawn_workers:
            raise ValueError("Worker agents cannot spawn additional agents")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.value
        return data


@dataclass
class VentureCell:
    """An isolated company-specific organization of specialized agents."""

    venture_id: str
    name: str
    thesis: str
    status: VentureCellStatus
    approval_policy: ApprovalPolicy
    agents: List[AgentBlueprint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def transition_to(self, status: VentureCellStatus) -> None:
        allowed = {
            VentureCellStatus.PROPOSED: {VentureCellStatus.APPROVED, VentureCellStatus.RETIRED},
            VentureCellStatus.APPROVED: {VentureCellStatus.PROVISIONING, VentureCellStatus.RETIRED},
            VentureCellStatus.PROVISIONING: {VentureCellStatus.ACTIVE, VentureCellStatus.PAUSED},
            VentureCellStatus.ACTIVE: {VentureCellStatus.PAUSED, VentureCellStatus.RETIRED},
            VentureCellStatus.PAUSED: {VentureCellStatus.ACTIVE, VentureCellStatus.RETIRED},
            VentureCellStatus.RETIRED: set(),
        }
        if status not in allowed[self.status]:
            raise ValueError(f"Invalid venture cell transition: {self.status.value} -> {status.value}")
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "venture_id": self.venture_id,
            "name": self.name,
            "thesis": self.thesis,
            "status": self.status.value,
            "approval_policy": self.approval_policy.to_dict(),
            "agents": [agent.to_dict() for agent in self.agents],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
