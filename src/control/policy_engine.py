"""Deterministic authorization for Venture Cell side effects."""

from __future__ import annotations

import math
import threading
from collections.abc import Mapping
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Iterable, Optional

from .evidence import EvidenceLedger
from .models import (
    ActionDefinition,
    ActionIntent,
    ApprovalRecord,
    AutonomyStage,
    CapabilityGrant,
    CellStatus,
    Incident,
    IncidentSeverity,
    PolicyDecision,
    PolicyDisposition,
    RiskTier,
    VentureCellCharter,
    utc_now,
)
from .promotion import (
    PromotionCriteria,
    PromotionEvaluation,
    PromotionEvaluator,
    PromotionEvidence,
)

if TYPE_CHECKING:
    from .state_store import SQLiteControlStateStore


class PolicyConfigurationError(ValueError):
    """Raised when a trusted authority attempts to install invalid policy."""


class AuthorizationError(PermissionError):
    """Raised when an actor attempts to administer authority it does not own."""


class PolicyEngine:
    """Fail-closed policy decision point for all consequential actions."""

    def __init__(
        self,
        *,
        root_authorities: Iterable[str],
        human_authorities: Iterable[str],
        evidence_ledger: Optional[EvidenceLedger] = None,
        policy_version: str = "v1",
        state_store: Optional["SQLiteControlStateStore"] = None,
    ) -> None:
        self.root_authorities = frozenset(root_authorities)
        self.human_authorities = frozenset(human_authorities) | self.root_authorities
        if not self.root_authorities:
            raise PolicyConfigurationError("at least one root authority is required")
        self.policy_version = policy_version
        self.ledger = evidence_ledger or EvidenceLedger()
        self.state_store = state_store
        self._action_definitions: dict[str, ActionDefinition] = {}
        self._cells: dict[str, VentureCellCharter] = {}
        self._grants: dict[str, CapabilityGrant] = {}
        self._approvals: dict[str, ApprovalRecord] = {}
        self._promotion_criteria: dict[
            tuple[str, AutonomyStage], PromotionCriteria
        ] = {}
        self._grant_daily_spend: dict[tuple[str, str], Decimal] = {}
        self._grant_total_spend: dict[str, Decimal] = {}
        self._cell_daily_spend: dict[tuple[str, str], Decimal] = {}
        self._cell_total_spend: dict[str, Decimal] = {}
        self._promotion_evaluator = PromotionEvaluator()
        self._lock = threading.RLock()
        self._persistence_healthy = True
        self._evidence_continuity = True
        if self.state_store is not None:
            stored_state = self.state_store.load_policy_state()
            if stored_state is not None:
                self._restore_state(stored_state)

    @property
    def action_definitions(self) -> dict[str, ActionDefinition]:
        return dict(self._action_definitions)

    @property
    def persistence_healthy(self) -> bool:
        """Return whether the last durable policy-state write succeeded."""

        return self._persistence_healthy

    @property
    def evidence_continuity(self) -> bool:
        """Return whether the configured ledger contains the stored anchor."""

        return self._evidence_continuity

    def list_cells(self) -> tuple[VentureCellCharter, ...]:
        """Return a stable snapshot of configured Venture Cells."""

        with self._lock:
            return tuple(
                sorted(self._cells.values(), key=lambda item: item.cell_id)
            )

    def list_grants(
        self,
        *,
        cell_id: str | None = None,
    ) -> tuple[CapabilityGrant, ...]:
        """Return a stable snapshot of grants, optionally scoped to one cell."""

        with self._lock:
            grants = self._grants.values()
            if cell_id is not None:
                grants = (
                    grant for grant in grants if grant.cell_id == cell_id
                )
            return tuple(sorted(grants, key=lambda item: item.grant_id))

    def get_cell(self, cell_id: str) -> Optional[VentureCellCharter]:
        return self._cells.get(cell_id)

    def get_grant(self, grant_id: str) -> Optional[CapabilityGrant]:
        return self._grants.get(grant_id)

    def get_promotion_criteria(
        self,
        action_type: str,
        target_stage: AutonomyStage,
    ) -> Optional[PromotionCriteria]:
        return self._promotion_criteria.get((action_type, target_stage))

    def export_state(self) -> Mapping[str, Any]:
        """Return the complete authorization state in a reconstructable form."""

        with self._lock:
            ledger_entries = self.ledger.entries
            ledger_anchor = (
                {
                    "sequence": ledger_entries[-1].sequence,
                    "entry_hash": ledger_entries[-1].entry_hash,
                }
                if ledger_entries
                else {"sequence": 0, "entry_hash": "0" * 64}
            )
            return {
                "schema_version": 1,
                "policy_version": self.policy_version,
                "root_authorities": sorted(self.root_authorities),
                "human_authorities": sorted(self.human_authorities),
                "ledger_anchor": ledger_anchor,
                "action_definitions": [
                    {
                        "action_type": definition.action_type,
                        "risk_tier": int(definition.risk_tier),
                        "minimum_stage": int(definition.minimum_stage),
                        "required_human_approvals": (
                            definition.required_human_approvals
                        ),
                        "description": definition.description,
                    }
                    for definition in sorted(
                        self._action_definitions.values(),
                        key=lambda item: item.action_type,
                    )
                ],
                "cells": [
                    {
                        "cell_id": cell.cell_id,
                        "mission": cell.mission,
                        "owner_id": cell.owner_id,
                        "allowed_geographies": sorted(cell.allowed_geographies),
                        "allowed_data_classes": sorted(cell.allowed_data_classes),
                        "prohibited_actions": sorted(cell.prohibited_actions),
                        "max_daily_spend_usd": str(cell.max_daily_spend_usd),
                        "max_total_spend_usd": str(cell.max_total_spend_usd),
                        "kill_conditions": list(cell.kill_conditions),
                        "policy_version": cell.policy_version,
                        "status": cell.status.value,
                        "created_at": cell.created_at.isoformat(),
                    }
                    for cell in sorted(
                        self._cells.values(), key=lambda item: item.cell_id
                    )
                ],
                "grants": [
                    {
                        "grant_id": grant.grant_id,
                        "cell_id": grant.cell_id,
                        "agent_id": grant.agent_id,
                        "action_type": grant.action_type,
                        "stage": int(grant.stage),
                        "resource_prefixes": list(grant.resource_prefixes),
                        "expires_at": grant.expires_at.isoformat(),
                        "context_fingerprint": grant.context_fingerprint,
                        "allowed_geographies": sorted(grant.allowed_geographies),
                        "allowed_data_classes": sorted(grant.allowed_data_classes),
                        "parameter_constraints": {
                            path: list(values)
                            for path, values in sorted(
                                grant.parameter_constraints.items()
                            )
                        },
                        "max_per_action_usd": str(grant.max_per_action_usd),
                        "max_daily_spend_usd": str(grant.max_daily_spend_usd),
                        "max_total_spend_usd": str(grant.max_total_spend_usd),
                        "delegation_depth": grant.delegation_depth,
                        "parent_grant_id": grant.parent_grant_id,
                        "created_by": grant.created_by,
                        "issued_at": grant.issued_at.isoformat(),
                        "active": grant.active,
                    }
                    for grant in sorted(
                        self._grants.values(), key=lambda item: item.grant_id
                    )
                ],
                "approvals": [
                    {
                        "approval_id": approval.approval_id,
                        "action_fingerprint": approval.action_fingerprint,
                        "approver_id": approval.approver_id,
                        "policy_version": approval.policy_version,
                        "expires_at": approval.expires_at.isoformat(),
                        "approved_at": approval.approved_at.isoformat(),
                    }
                    for approval in sorted(
                        self._approvals.values(),
                        key=lambda item: item.approval_id,
                    )
                ],
                "promotion_criteria": [
                    {
                        "action_type": action_type,
                        "target_stage": int(target_stage),
                        "minimum_trials": criteria.minimum_trials,
                        "minimum_observation_days": (
                            criteria.minimum_observation_days
                        ),
                        "maximum_failure_upper_bound": (
                            criteria.maximum_failure_upper_bound
                        ),
                        "minimum_audit_completeness": (
                            criteria.minimum_audit_completeness
                        ),
                        "minimum_rollback_drills": (
                            criteria.minimum_rollback_drills
                        ),
                        "require_red_team": criteria.require_red_team,
                        "maximum_policy_violations": (
                            criteria.maximum_policy_violations
                        ),
                        "maximum_critical_incidents": (
                            criteria.maximum_critical_incidents
                        ),
                        "maximum_red_team_critical_findings": (
                            criteria.maximum_red_team_critical_findings
                        ),
                    }
                    for (action_type, target_stage), criteria in sorted(
                        self._promotion_criteria.items(),
                        key=lambda item: (item[0][0], int(item[0][1])),
                    )
                ],
                "spend": {
                    "grant_daily": [
                        {
                            "grant_id": grant_id,
                            "day": day,
                            "amount_usd": str(amount),
                        }
                        for (grant_id, day), amount in sorted(
                            self._grant_daily_spend.items()
                        )
                    ],
                    "grant_total": [
                        {"grant_id": grant_id, "amount_usd": str(amount)}
                        for grant_id, amount in sorted(
                            self._grant_total_spend.items()
                        )
                    ],
                    "cell_daily": [
                        {
                            "cell_id": cell_id,
                            "day": day,
                            "amount_usd": str(amount),
                        }
                        for (cell_id, day), amount in sorted(
                            self._cell_daily_spend.items()
                        )
                    ],
                    "cell_total": [
                        {"cell_id": cell_id, "amount_usd": str(amount)}
                        for cell_id, amount in sorted(
                            self._cell_total_spend.items()
                        )
                    ],
                },
            }

    def _restore_state(self, payload: Mapping[str, Any]) -> None:
        """Reconstruct policy state only when identity and schema still match."""

        if payload.get("schema_version") != 1:
            raise PolicyConfigurationError("unsupported policy snapshot schema")
        if payload.get("policy_version") != self.policy_version:
            raise PolicyConfigurationError("stored policy version does not match runtime")
        if frozenset(payload.get("root_authorities", ())) != self.root_authorities:
            raise PolicyConfigurationError("stored root authorities do not match runtime")
        if frozenset(payload.get("human_authorities", ())) != self.human_authorities:
            raise PolicyConfigurationError("stored human authorities do not match runtime")

        ledger_anchor = payload.get("ledger_anchor")
        if not isinstance(ledger_anchor, Mapping):
            raise PolicyConfigurationError("policy snapshot lacks a ledger anchor")
        try:
            anchor_sequence = int(ledger_anchor["sequence"])
            anchor_hash = str(ledger_anchor["entry_hash"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PolicyConfigurationError("invalid policy ledger anchor") from exc
        self._evidence_continuity = self._ledger_contains_anchor(
            anchor_sequence,
            anchor_hash,
        )

        try:
            definitions = {
                item["action_type"]: ActionDefinition(
                    action_type=item["action_type"],
                    risk_tier=RiskTier(int(item["risk_tier"])),
                    minimum_stage=AutonomyStage(int(item["minimum_stage"])),
                    required_human_approvals=int(
                        item.get("required_human_approvals", 0)
                    ),
                    description=item.get("description", ""),
                )
                for item in payload.get("action_definitions", ())
            }
            cells = {
                item["cell_id"]: VentureCellCharter(
                    cell_id=item["cell_id"],
                    mission=item["mission"],
                    owner_id=item["owner_id"],
                    allowed_geographies=frozenset(
                        item.get("allowed_geographies", ())
                    ),
                    allowed_data_classes=frozenset(
                        item.get("allowed_data_classes", ())
                    ),
                    prohibited_actions=frozenset(
                        item.get("prohibited_actions", ())
                    ),
                    max_daily_spend_usd=Decimal(item["max_daily_spend_usd"]),
                    max_total_spend_usd=Decimal(item["max_total_spend_usd"]),
                    kill_conditions=tuple(item.get("kill_conditions", ())),
                    policy_version=item["policy_version"],
                    status=CellStatus(item["status"]),
                    created_at=self._parse_snapshot_datetime(item["created_at"]),
                )
                for item in payload.get("cells", ())
            }
            grants = {
                item["grant_id"]: CapabilityGrant(
                    grant_id=item["grant_id"],
                    cell_id=item["cell_id"],
                    agent_id=item["agent_id"],
                    action_type=item["action_type"],
                    stage=AutonomyStage(int(item["stage"])),
                    resource_prefixes=tuple(item["resource_prefixes"]),
                    expires_at=self._parse_snapshot_datetime(item["expires_at"]),
                    context_fingerprint=item["context_fingerprint"],
                    allowed_geographies=frozenset(
                        item.get("allowed_geographies", ())
                    ),
                    allowed_data_classes=frozenset(
                        item.get("allowed_data_classes", ())
                    ),
                    parameter_constraints={
                        path: tuple(values)
                        for path, values in item.get(
                            "parameter_constraints", {}
                        ).items()
                    },
                    max_per_action_usd=Decimal(item["max_per_action_usd"]),
                    max_daily_spend_usd=Decimal(item["max_daily_spend_usd"]),
                    max_total_spend_usd=Decimal(item["max_total_spend_usd"]),
                    delegation_depth=int(item.get("delegation_depth", 0)),
                    parent_grant_id=item.get("parent_grant_id"),
                    created_by=item.get("created_by", ""),
                    issued_at=self._parse_snapshot_datetime(item["issued_at"]),
                    active=bool(item.get("active", True)),
                )
                for item in payload.get("grants", ())
            }
            approvals = {
                item["approval_id"]: ApprovalRecord(
                    approval_id=item["approval_id"],
                    action_fingerprint=item["action_fingerprint"],
                    approver_id=item["approver_id"],
                    policy_version=item["policy_version"],
                    expires_at=self._parse_snapshot_datetime(item["expires_at"]),
                    approved_at=self._parse_snapshot_datetime(item["approved_at"]),
                )
                for item in payload.get("approvals", ())
            }
            criteria = {
                (item["action_type"], AutonomyStage(int(item["target_stage"]))): (
                    PromotionCriteria(
                        minimum_trials=int(item["minimum_trials"]),
                        minimum_observation_days=int(
                            item["minimum_observation_days"]
                        ),
                        maximum_failure_upper_bound=float(
                            item["maximum_failure_upper_bound"]
                        ),
                        minimum_audit_completeness=float(
                            item.get("minimum_audit_completeness", 1.0)
                        ),
                        minimum_rollback_drills=int(
                            item.get("minimum_rollback_drills", 1)
                        ),
                        require_red_team=bool(item.get("require_red_team", True)),
                        maximum_policy_violations=int(
                            item.get("maximum_policy_violations", 0)
                        ),
                        maximum_critical_incidents=int(
                            item.get("maximum_critical_incidents", 0)
                        ),
                        maximum_red_team_critical_findings=int(
                            item.get("maximum_red_team_critical_findings", 0)
                        ),
                    )
                )
                for item in payload.get("promotion_criteria", ())
            }
            spend = payload.get("spend", {})
            grant_daily = {
                (item["grant_id"], item["day"]): Decimal(item["amount_usd"])
                for item in spend.get("grant_daily", ())
            }
            grant_total = {
                item["grant_id"]: Decimal(item["amount_usd"])
                for item in spend.get("grant_total", ())
            }
            cell_daily = {
                (item["cell_id"], item["day"]): Decimal(item["amount_usd"])
                for item in spend.get("cell_daily", ())
            }
            cell_total = {
                item["cell_id"]: Decimal(item["amount_usd"])
                for item in spend.get("cell_total", ())
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise PolicyConfigurationError("invalid durable policy snapshot") from exc

        self._reject_duplicate_snapshot_ids(
            payload,
            definitions,
            cells,
            grants,
            approvals,
            criteria,
            grant_daily,
            grant_total,
            cell_daily,
            cell_total,
        )
        self._validate_restored_state(
            definitions,
            cells,
            grants,
            approvals,
            criteria,
            grant_daily,
            grant_total,
            cell_daily,
            cell_total,
        )
        self._action_definitions = definitions
        self._cells = cells
        self._grants = grants
        self._approvals = approvals
        self._promotion_criteria = criteria
        self._grant_daily_spend = grant_daily
        self._grant_total_spend = grant_total
        self._cell_daily_spend = cell_daily
        self._cell_total_spend = cell_total

    def register_action_definition(
        self,
        actor_id: str,
        definition: ActionDefinition,
    ) -> None:
        self._require_root(actor_id)
        if not definition.action_type:
            raise PolicyConfigurationError("action_type is required")
        if definition.risk_tier is RiskTier.MATERIAL and definition.required_human_approvals < 2:
            raise PolicyConfigurationError("material actions require dual human control")
        if definition.risk_tier is RiskTier.CONSTITUTIONAL and definition.required_human_approvals:
            raise PolicyConfigurationError("constitutional actions must be denied, not approval-routed")
        with self._lock:
            self._action_definitions[definition.action_type] = definition
            self.ledger.append(
                "action_definition_registered",
                actor_id,
                {
                    "action_type": definition.action_type,
                    "risk_tier": definition.risk_tier,
                    "minimum_stage": definition.minimum_stage,
                    "required_human_approvals": definition.required_human_approvals,
                    "policy_version": self.policy_version,
                },
            )
            self._persist_state()

    def set_promotion_criteria(
        self,
        actor_id: str,
        action_type: str,
        target_stage: AutonomyStage,
        criteria: PromotionCriteria,
    ) -> None:
        self._require_root(actor_id)
        if action_type not in self._action_definitions:
            raise PolicyConfigurationError("unknown action type")
        if target_stage is AutonomyStage.SIMULATE:
            raise PolicyConfigurationError("SIMULATE is not a promotion target")
        with self._lock:
            self._promotion_criteria[(action_type, target_stage)] = criteria
            self.ledger.append(
                "promotion_criteria_registered",
                actor_id,
                {
                    "action_type": action_type,
                    "target_stage": target_stage,
                    "criteria": criteria,
                    "policy_version": self.policy_version,
                },
            )
            self._persist_state()

    def create_cell(self, actor_id: str, charter: VentureCellCharter) -> None:
        self._require_root(actor_id)
        if charter.policy_version != self.policy_version:
            raise PolicyConfigurationError("charter policy version is stale")
        if not charter.cell_id or not charter.mission or not charter.owner_id:
            raise PolicyConfigurationError("cell_id, mission, and owner_id are required")
        self._validate_money(charter.max_daily_spend_usd)
        self._validate_money(charter.max_total_spend_usd)
        if charter.max_daily_spend_usd > charter.max_total_spend_usd:
            raise PolicyConfigurationError("daily cell budget cannot exceed total budget")
        with self._lock:
            if charter.cell_id in self._cells:
                raise PolicyConfigurationError("cell already exists")
            self._cells[charter.cell_id] = charter
            self.ledger.append(
                "cell_created",
                actor_id,
                {
                    "mission": charter.mission,
                    "owner_id": charter.owner_id,
                    "allowed_geographies": charter.allowed_geographies,
                    "allowed_data_classes": charter.allowed_data_classes,
                    "daily_budget_usd": charter.max_daily_spend_usd,
                    "total_budget_usd": charter.max_total_spend_usd,
                    "policy_version": charter.policy_version,
                },
                cell_id=charter.cell_id,
            )
            self._persist_state()

    def pause_cell(self, actor_id: str, cell_id: str, reason: str) -> None:
        self._require_human(actor_id)
        self._set_cell_status(actor_id, cell_id, CellStatus.PAUSED, reason)

    def resume_cell(self, actor_id: str, cell_id: str, reason: str) -> None:
        self._require_root(actor_id)
        self._set_cell_status(actor_id, cell_id, CellStatus.ACTIVE, reason)

    def terminate_cell(self, actor_id: str, cell_id: str, reason: str) -> None:
        self._require_root(actor_id)
        self._set_cell_status(actor_id, cell_id, CellStatus.TERMINATED, reason)

    def issue_grant(self, actor_id: str, grant: CapabilityGrant) -> CapabilityGrant:
        self._require_root(actor_id)
        if grant.stage > AutonomyStage.SHADOW:
            raise AuthorizationError(
                "new root grants must start in SIMULATE or SHADOW; "
                "executable stages require evidence-gated promotion"
            )
        with self._lock:
            self._validate_grant(grant)
            if grant.parent_grant_id is not None:
                raise PolicyConfigurationError("root grants cannot claim a parent")
            installed = replace(grant, created_by=actor_id)
            self._store_grant(installed, actor_id, "capability_grant_issued")
            return installed

    def delegate_grant(
        self,
        actor_id: str,
        parent_grant_id: str,
        child_grant: CapabilityGrant,
    ) -> CapabilityGrant:
        """Delegate only a strict, short-lived subset of an existing grant."""

        with self._lock:
            parent = self._grants.get(parent_grant_id)
            if parent is None:
                raise PolicyConfigurationError("parent grant not found")
            if actor_id != parent.agent_id:
                raise AuthorizationError("only the grantee can delegate this capability")
            if not parent.active or self._is_expired(parent.expires_at):
                raise AuthorizationError("parent grant is inactive or expired")
            definition = self._action_definitions[parent.action_type]
            if definition.risk_tier >= RiskTier.MATERIAL:
                raise AuthorizationError("material authority is not delegable")
            if parent.delegation_depth <= 0:
                raise AuthorizationError("parent grant has no delegation depth")

            installed = replace(
                child_grant,
                parent_grant_id=parent.grant_id,
                created_by=actor_id,
            )
            self._validate_grant(installed)
            self._validate_strict_subset(parent, installed)
            self._store_grant(installed, actor_id, "capability_grant_delegated")
            return installed

    def revoke_grant(self, actor_id: str, grant_id: str, reason: str) -> None:
        self._require_root(actor_id)
        with self._lock:
            grant = self._require_grant(grant_id)
            self._grants[grant_id] = replace(grant, active=False)
            self.ledger.append(
                "capability_grant_revoked",
                actor_id,
                {"grant_id": grant_id, "reason": reason},
                cell_id=grant.cell_id,
            )
            self._persist_state()

    def record_approval(self, approval: ApprovalRecord) -> None:
        self._require_human(approval.approver_id)
        if approval.policy_version != self.policy_version:
            raise AuthorizationError("approval is bound to a stale policy")
        if self._is_expired(approval.expires_at):
            raise AuthorizationError("approval has expired")
        with self._lock:
            if approval.approval_id in self._approvals:
                if self._approvals[approval.approval_id] != approval:
                    raise PolicyConfigurationError("approval id collision")
                return
            self._approvals[approval.approval_id] = approval
            self.ledger.append(
                "human_approval_recorded",
                approval.approver_id,
                {
                    "approval_id": approval.approval_id,
                    "action_fingerprint": approval.action_fingerprint,
                    "expires_at": approval.expires_at,
                    "policy_version": approval.policy_version,
                },
            )
            self._persist_state()

    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        """Evaluate an intent against installed policy; unknowns fail closed."""

        with self._lock:
            if not self._persistence_healthy:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("control_state_persistence_unavailable",),
                    self._action_definitions.get(intent.action_type),
                )
            definition = self._action_definitions.get(intent.action_type)
            if definition is None:
                return self._decision(intent, PolicyDisposition.DENY, ("unknown_action",))

            cell = self._cells.get(intent.cell_id)
            if cell is None:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("unknown_cell",),
                    definition,
                )
            if cell.status is not CellStatus.ACTIVE:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    (f"cell_{cell.status.value}",),
                    definition,
                )
            if cell.policy_version != self.policy_version:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("stale_charter",),
                    definition,
                )
            if intent.action_type in cell.prohibited_actions:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("charter_prohibition",),
                    definition,
                )
            if definition.risk_tier is RiskTier.CONSTITUTIONAL:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("constitutional_action_non_delegable",),
                    definition,
                )
            if intent.amount_usd < 0:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("invalid_negative_amount",),
                    definition,
                )
            if intent.geography and intent.geography not in cell.allowed_geographies:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("geography_outside_charter",),
                    definition,
                )
            if not intent.data_classes.issubset(cell.allowed_data_classes):
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("data_class_outside_charter",),
                    definition,
                )

            grant = self._select_grant(intent)
            if grant is None:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("no_active_capability_grant",),
                    definition,
                )
            if intent.context_fingerprint != grant.context_fingerprint:
                return self._decision(
                    intent,
                    PolicyDisposition.SHADOW,
                    ("context_changed_revalidation_required",),
                    definition,
                    grant,
                )
            if intent.geography and intent.geography not in grant.allowed_geographies:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("geography_outside_grant",),
                    definition,
                    grant,
                )
            if not intent.data_classes.issubset(grant.allowed_data_classes):
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    ("data_class_outside_grant",),
                    definition,
                    grant,
                )
            parameter_reason = self._parameter_violation(intent, grant)
            if parameter_reason:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    (parameter_reason,),
                    definition,
                    grant,
                )
            if grant.stage <= AutonomyStage.SHADOW:
                return self._decision(
                    intent,
                    PolicyDisposition.SHADOW,
                    ("capability_is_observation_only",),
                    definition,
                    grant,
                )
            if grant.stage < definition.minimum_stage:
                return self._decision(
                    intent,
                    PolicyDisposition.SHADOW,
                    ("capability_stage_below_action_minimum",),
                    definition,
                    grant,
                )

            budget_reason = self._budget_violation(intent, grant, cell)
            if budget_reason:
                return self._decision(
                    intent,
                    PolicyDisposition.DENY,
                    (budget_reason,),
                    definition,
                    grant,
                )

            valid_approvers = self._valid_approvers(intent)
            required_approvals = definition.required_human_approvals
            if len(valid_approvers) < required_approvals:
                return self._decision(
                    intent,
                    PolicyDisposition.REVIEW,
                    ("human_approval_required",),
                    definition,
                    grant,
                    valid_approvals=len(valid_approvers),
                )

            return self._decision(
                intent,
                PolicyDisposition.ALLOW,
                ("authorized",),
                definition,
                grant,
                valid_approvals=len(valid_approvers),
            )

    def record_execution(self, intent: ActionIntent, grant_id: str) -> None:
        """Commit spend counters after the gateway reports successful execution."""

        with self._lock:
            grant = self._require_grant(grant_id)
            if grant.cell_id != intent.cell_id or grant.agent_id != intent.agent_id:
                raise AuthorizationError("receipt does not match the capability grant")
            day = utc_now().date().isoformat()
            amount = intent.amount_usd
            self._grant_daily_spend[(grant_id, day)] = (
                self._grant_daily_spend.get((grant_id, day), Decimal("0")) + amount
            )
            self._grant_total_spend[grant_id] = (
                self._grant_total_spend.get(grant_id, Decimal("0")) + amount
            )
            self._cell_daily_spend[(intent.cell_id, day)] = (
                self._cell_daily_spend.get((intent.cell_id, day), Decimal("0")) + amount
            )
            self._cell_total_spend[intent.cell_id] = (
                self._cell_total_spend.get(intent.cell_id, Decimal("0")) + amount
            )
            self._persist_state()

    def promote_grant(
        self,
        actor_id: str,
        grant_id: str,
        evidence: PromotionEvidence,
        independent_review_id: str,
    ) -> PromotionEvaluation:
        """Advance exactly one stage after independent, policy-defined assurance."""

        self._require_root(actor_id)
        with self._lock:
            if not self._evidence_continuity:
                raise AuthorizationError(
                    "durable evidence ledger continuity is required for promotion"
                )
            grant = self._require_grant(grant_id)
            if actor_id == grant.agent_id:
                raise AuthorizationError("agents cannot approve their own promotion")
            if not independent_review_id:
                raise PolicyConfigurationError("independent review id is required")
            if grant.stage is AutonomyStage.SCALED_BOUNDED:
                raise PolicyConfigurationError("grant is already at the maximum stage")
            if evidence.context_fingerprint != grant.context_fingerprint:
                evaluation = PromotionEvaluation(
                    passed=False,
                    reasons=("context_evidence_mismatch",),
                    failure_upper_bound=1.0,
                )
                self._record_promotion_decision(
                    actor_id,
                    grant,
                    evidence,
                    evaluation,
                    independent_review_id,
                )
                return evaluation
            if not self.ledger.verify_chain():
                raise AuthorizationError("evidence ledger integrity check failed")

            target_stage = AutonomyStage(grant.stage + 1)
            criteria = self._promotion_criteria.get((grant.action_type, target_stage))
            if criteria is None:
                raise PolicyConfigurationError("promotion criteria are not configured")
            evaluation = self._promotion_evaluator.evaluate(evidence, criteria)
            self._record_promotion_decision(
                actor_id,
                grant,
                evidence,
                evaluation,
                independent_review_id,
            )
            if evaluation.passed:
                self._grants[grant_id] = replace(grant, stage=target_stage)
                self._persist_state()
            return evaluation

    def regress_grant(
        self,
        actor_id: str,
        grant_id: str,
        target_stage: AutonomyStage,
        reason: str,
    ) -> CapabilityGrant:
        self._require_human(actor_id)
        with self._lock:
            return self._regress_grant(actor_id, grant_id, target_stage, reason)

    def report_incident(self, incident: Incident) -> None:
        """Any authenticated reporter may reduce authority; none may increase it."""

        with self._lock:
            cell = self._cells.get(incident.cell_id)
            if cell is None:
                raise PolicyConfigurationError("incident references an unknown cell")
            self.ledger.append(
                "incident_reported",
                incident.actor_id,
                {
                    "incident_id": incident.incident_id,
                    "severity": incident.severity,
                    "reason": incident.reason,
                    "grant_id": incident.grant_id,
                },
                cell_id=incident.cell_id,
            )
            if incident.severity is IncidentSeverity.CRITICAL:
                self._cells[incident.cell_id] = replace(cell, status=CellStatus.PAUSED)
                self.ledger.append(
                    "cell_auto_paused",
                    "policy-engine",
                    {"incident_id": incident.incident_id, "reason": incident.reason},
                    cell_id=incident.cell_id,
                )
            elif incident.severity is IncidentSeverity.MAJOR:
                affected = (
                    [incident.grant_id]
                    if incident.grant_id
                    else [
                        grant.grant_id
                        for grant in self._grants.values()
                        if grant.cell_id == incident.cell_id and grant.active
                    ]
                )
                for grant_id in affected:
                    grant = self._grants.get(grant_id)
                    if grant and grant.stage > AutonomyStage.SIMULATE:
                        self._regress_grant(
                            "policy-engine",
                            grant_id,
                            AutonomyStage(grant.stage - 1),
                            f"automatic regression after {incident.incident_id}",
                        )
            self._persist_state()

    @staticmethod
    def _parse_snapshot_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("snapshot timestamps must be timezone-aware")
        return parsed

    def _ledger_contains_anchor(self, sequence: int, entry_hash: str) -> bool:
        if sequence < 0 or not self.ledger.verify_chain():
            return False
        if sequence == 0:
            return entry_hash == "0" * 64
        entries = self.ledger.entries
        if len(entries) < sequence:
            return False
        anchored = entries[sequence - 1]
        return anchored.sequence == sequence and anchored.entry_hash == entry_hash

    @staticmethod
    def _reject_duplicate_snapshot_ids(
        payload: Mapping[str, Any],
        definitions: Mapping[str, ActionDefinition],
        cells: Mapping[str, VentureCellCharter],
        grants: Mapping[str, CapabilityGrant],
        approvals: Mapping[str, ApprovalRecord],
        criteria: Mapping[tuple[str, AutonomyStage], PromotionCriteria],
        grant_daily: Mapping[tuple[str, str], Decimal],
        grant_total: Mapping[str, Decimal],
        cell_daily: Mapping[tuple[str, str], Decimal],
        cell_total: Mapping[str, Decimal],
    ) -> None:
        sections = (
            ("action_definitions", definitions),
            ("cells", cells),
            ("grants", grants),
            ("approvals", approvals),
        )
        for section_name, decoded in sections:
            encoded = payload.get(section_name, ())
            if not isinstance(encoded, list) or len(encoded) != len(decoded):
                raise PolicyConfigurationError(
                    f"duplicate or malformed records in {section_name}"
                )
        promotion_records = payload.get("promotion_criteria", ())
        if (
            not isinstance(promotion_records, list)
            or len(promotion_records) != len(criteria)
        ):
            raise PolicyConfigurationError(
                "duplicate or malformed records in promotion_criteria"
            )
        spend = payload.get("spend")
        if not isinstance(spend, Mapping):
            raise PolicyConfigurationError("malformed spend snapshot")
        spend_sections = (
            ("grant_daily", grant_daily),
            ("grant_total", grant_total),
            ("cell_daily", cell_daily),
            ("cell_total", cell_total),
        )
        for section_name, decoded in spend_sections:
            encoded = spend.get(section_name, ())
            if not isinstance(encoded, list) or len(encoded) != len(decoded):
                raise PolicyConfigurationError(
                    f"duplicate or malformed records in spend.{section_name}"
                )

    def _validate_restored_state(
        self,
        definitions: Mapping[str, ActionDefinition],
        cells: Mapping[str, VentureCellCharter],
        grants: Mapping[str, CapabilityGrant],
        approvals: Mapping[str, ApprovalRecord],
        criteria: Mapping[tuple[str, AutonomyStage], PromotionCriteria],
        grant_daily: Mapping[tuple[str, str], Decimal],
        grant_total: Mapping[str, Decimal],
        cell_daily: Mapping[tuple[str, str], Decimal],
        cell_total: Mapping[str, Decimal],
    ) -> None:
        for action_type, definition in definitions.items():
            if not action_type or action_type != definition.action_type:
                raise PolicyConfigurationError("invalid restored action definition")
            if (
                definition.risk_tier is RiskTier.MATERIAL
                and definition.required_human_approvals < 2
            ):
                raise PolicyConfigurationError(
                    "restored material action lacks dual control"
                )
            if (
                definition.risk_tier is RiskTier.CONSTITUTIONAL
                and definition.required_human_approvals
            ):
                raise PolicyConfigurationError(
                    "restored constitutional action is approval-routed"
                )

        for cell_id, cell in cells.items():
            if (
                not cell_id
                or cell_id != cell.cell_id
                or not cell.mission
                or not cell.owner_id
                or cell.policy_version != self.policy_version
            ):
                raise PolicyConfigurationError("invalid restored cell charter")
            self._validate_money(cell.max_daily_spend_usd)
            self._validate_money(cell.max_total_spend_usd)
            if cell.max_daily_spend_usd > cell.max_total_spend_usd:
                raise PolicyConfigurationError("restored cell budget is inconsistent")

        for grant_id, grant in grants.items():
            cell = cells.get(grant.cell_id)
            definition = definitions.get(grant.action_type)
            if (
                not grant_id
                or grant_id != grant.grant_id
                or cell is None
                or definition is None
                or definition.risk_tier is RiskTier.CONSTITUTIONAL
                or not grant.agent_id
                or not grant.resource_prefixes
                or any(not prefix for prefix in grant.resource_prefixes)
                or not grant.context_fingerprint
            ):
                raise PolicyConfigurationError("invalid restored capability grant")
            if grant.expires_at.tzinfo is None or grant.expires_at.utcoffset() is None:
                raise PolicyConfigurationError("restored grant expiry is timezone-naive")
            if grant.delegation_depth < 0 or grant.delegation_depth > 2:
                raise PolicyConfigurationError("restored delegation depth is invalid")
            if (
                definition.risk_tier >= RiskTier.MATERIAL
                and grant.delegation_depth
            ):
                raise PolicyConfigurationError(
                    "restored material authority is delegable"
                )
            if not grant.allowed_geographies.issubset(cell.allowed_geographies):
                raise PolicyConfigurationError("restored grant geography is too broad")
            if not grant.allowed_data_classes.issubset(cell.allowed_data_classes):
                raise PolicyConfigurationError("restored grant data scope is too broad")
            for amount in (
                grant.max_per_action_usd,
                grant.max_daily_spend_usd,
                grant.max_total_spend_usd,
            ):
                self._validate_money(amount)
            if (
                grant.max_per_action_usd > grant.max_daily_spend_usd
                or grant.max_daily_spend_usd > grant.max_total_spend_usd
                or grant.max_daily_spend_usd > cell.max_daily_spend_usd
                or grant.max_total_spend_usd > cell.max_total_spend_usd
            ):
                raise PolicyConfigurationError("restored grant budget is inconsistent")
            if grant.parent_grant_id is not None and grant.parent_grant_id not in grants:
                raise PolicyConfigurationError("restored parent grant is missing")
            for path, allowed_values in grant.parameter_constraints.items():
                if not path or not allowed_values:
                    raise PolicyConfigurationError(
                        "restored parameter constraint is empty"
                    )
                for allowed_value in allowed_values:
                    self._validate_parameter_value(allowed_value)

        for approval_id, approval in approvals.items():
            if (
                not approval_id
                or approval_id != approval.approval_id
                or not approval.action_fingerprint
                or approval.approver_id not in self.human_authorities
                or approval.policy_version != self.policy_version
            ):
                raise PolicyConfigurationError("invalid restored approval")

        for (action_type, target_stage), item in criteria.items():
            if action_type not in definitions or target_stage is AutonomyStage.SIMULATE:
                raise PolicyConfigurationError("invalid restored promotion criteria")
            if (
                item.minimum_trials < 1
                or item.minimum_observation_days < 0
                or not 0 < item.maximum_failure_upper_bound <= 1
                or not 0 <= item.minimum_audit_completeness <= 1
                or item.minimum_rollback_drills < 0
                or item.maximum_policy_violations < 0
                or item.maximum_critical_incidents < 0
                or item.maximum_red_team_critical_findings < 0
            ):
                raise PolicyConfigurationError("restored promotion criteria are invalid")

        for (grant_id, day), amount in grant_daily.items():
            if grant_id not in grants:
                raise PolicyConfigurationError("restored grant spend has no grant")
            date.fromisoformat(day)
            self._validate_money(amount)
        for grant_id, amount in grant_total.items():
            if grant_id not in grants:
                raise PolicyConfigurationError("restored grant total has no grant")
            self._validate_money(amount)
        for (cell_id, day), amount in cell_daily.items():
            if cell_id not in cells:
                raise PolicyConfigurationError("restored cell spend has no cell")
            date.fromisoformat(day)
            self._validate_money(amount)
        for cell_id, amount in cell_total.items():
            if cell_id not in cells:
                raise PolicyConfigurationError("restored cell total has no cell")
            self._validate_money(amount)

    def _persist_state(self) -> None:
        if self.state_store is None:
            return
        try:
            self.state_store.save_policy_state(self.export_state())
        except Exception:
            self._persistence_healthy = False
            raise
        self._persistence_healthy = True

    def _require_root(self, actor_id: str) -> None:
        if actor_id not in self.root_authorities:
            raise AuthorizationError("root authority required")

    def _require_human(self, actor_id: str) -> None:
        if actor_id not in self.human_authorities:
            raise AuthorizationError("registered human authority required")

    @staticmethod
    def _validate_money(amount: Decimal) -> None:
        if amount < 0 or not amount.is_finite():
            raise PolicyConfigurationError("budget values must be finite and non-negative")

    @staticmethod
    def _validate_parameter_value(value: Any) -> None:
        """Limit persisted constraints to deterministic JSON value types."""

        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise PolicyConfigurationError(
                    "parameter constraint numbers must be finite"
                )
            return
        if isinstance(value, list):
            for item in value:
                PolicyEngine._validate_parameter_value(item)
            return
        if isinstance(value, Mapping):
            if any(not isinstance(key, str) for key in value):
                raise PolicyConfigurationError(
                    "parameter constraint object keys must be strings"
                )
            for item in value.values():
                PolicyEngine._validate_parameter_value(item)
            return
        raise PolicyConfigurationError(
            "parameter constraints must use deterministic JSON value types"
        )

    @staticmethod
    def _is_expired(expires_at: datetime) -> bool:
        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise PolicyConfigurationError("expiry timestamps must be timezone-aware")
        return expires_at <= utc_now()

    def _set_cell_status(
        self,
        actor_id: str,
        cell_id: str,
        status: CellStatus,
        reason: str,
    ) -> None:
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                raise PolicyConfigurationError("cell not found")
            if cell.status is CellStatus.TERMINATED and status is not CellStatus.TERMINATED:
                raise AuthorizationError("terminated cells cannot be reactivated")
            self._cells[cell_id] = replace(cell, status=status)
            self.ledger.append(
                f"cell_{status.value}",
                actor_id,
                {"reason": reason},
                cell_id=cell_id,
            )
            self._persist_state()

    def _validate_grant(self, grant: CapabilityGrant) -> None:
        if grant.grant_id in self._grants:
            raise PolicyConfigurationError("grant already exists")
        cell = self._cells.get(grant.cell_id)
        if cell is None or cell.status is not CellStatus.ACTIVE:
            raise PolicyConfigurationError("grant requires an active cell")
        definition = self._action_definitions.get(grant.action_type)
        if definition is None:
            raise PolicyConfigurationError("grant references an unknown action")
        if definition.risk_tier is RiskTier.CONSTITUTIONAL:
            raise AuthorizationError("constitutional actions cannot be granted")
        if not grant.agent_id or not grant.resource_prefixes:
            raise PolicyConfigurationError("agent and resource scope are required")
        if any(not prefix for prefix in grant.resource_prefixes):
            raise PolicyConfigurationError("resource prefixes cannot be empty")
        if not grant.context_fingerprint:
            raise PolicyConfigurationError("context fingerprint is required")
        for path, allowed_values in grant.parameter_constraints.items():
            if not path or not allowed_values:
                raise PolicyConfigurationError(
                    "parameter constraints require a path and allowed values"
                )
            for allowed_value in allowed_values:
                self._validate_parameter_value(allowed_value)
        if self._is_expired(grant.expires_at):
            raise PolicyConfigurationError("grant expiry must be in the future")
        if grant.delegation_depth < 0 or grant.delegation_depth > 2:
            raise PolicyConfigurationError("delegation depth must be between zero and two")
        if definition.risk_tier >= RiskTier.MATERIAL and grant.delegation_depth:
            raise AuthorizationError("material authority cannot be delegated")
        if not grant.allowed_geographies.issubset(cell.allowed_geographies):
            raise PolicyConfigurationError("grant geography exceeds the charter")
        if not grant.allowed_data_classes.issubset(cell.allowed_data_classes):
            raise PolicyConfigurationError("grant data scope exceeds the charter")
        for amount in (
            grant.max_per_action_usd,
            grant.max_daily_spend_usd,
            grant.max_total_spend_usd,
        ):
            self._validate_money(amount)
        if grant.max_per_action_usd > grant.max_daily_spend_usd:
            raise PolicyConfigurationError("per-action budget exceeds daily grant budget")
        if grant.max_daily_spend_usd > grant.max_total_spend_usd:
            raise PolicyConfigurationError("daily grant budget exceeds total grant budget")
        if grant.max_daily_spend_usd > cell.max_daily_spend_usd:
            raise PolicyConfigurationError("grant daily budget exceeds the charter")
        if grant.max_total_spend_usd > cell.max_total_spend_usd:
            raise PolicyConfigurationError("grant total budget exceeds the charter")

    def _validate_strict_subset(
        self,
        parent: CapabilityGrant,
        child: CapabilityGrant,
    ) -> None:
        if child.cell_id != parent.cell_id or child.action_type != parent.action_type:
            raise AuthorizationError("delegation must remain in the same cell and capability")
        if child.agent_id == parent.agent_id:
            raise AuthorizationError("delegation must target a distinct child agent")
        if child.stage > parent.stage:
            raise AuthorizationError("child stage exceeds parent stage")
        if child.context_fingerprint != parent.context_fingerprint:
            raise AuthorizationError("child context must match parent context")
        if child.expires_at > parent.expires_at:
            raise AuthorizationError("child expiry exceeds parent expiry")
        if child.delegation_depth >= parent.delegation_depth:
            raise AuthorizationError("child delegation depth is not a strict subset")
        if not child.allowed_geographies.issubset(parent.allowed_geographies):
            raise AuthorizationError("child geography exceeds parent scope")
        if not child.allowed_data_classes.issubset(parent.allowed_data_classes):
            raise AuthorizationError("child data scope exceeds parent scope")
        for path, parent_values in parent.parameter_constraints.items():
            child_values = child.parameter_constraints.get(path)
            if child_values is None or any(
                value not in parent_values for value in child_values
            ):
                raise AuthorizationError("child parameter scope exceeds parent scope")
        if any(
            not any(prefix.startswith(parent_prefix) for parent_prefix in parent.resource_prefixes)
            for prefix in child.resource_prefixes
        ):
            raise AuthorizationError("child resource scope exceeds parent scope")
        if child.max_per_action_usd > parent.max_per_action_usd:
            raise AuthorizationError("child per-action budget exceeds parent budget")
        if child.max_daily_spend_usd > parent.max_daily_spend_usd:
            raise AuthorizationError("child daily budget exceeds parent budget")
        if child.max_total_spend_usd > parent.max_total_spend_usd:
            raise AuthorizationError("child total budget exceeds parent budget")

        strict = any(
            (
                child.stage < parent.stage,
                child.expires_at < parent.expires_at,
                child.delegation_depth < parent.delegation_depth,
                child.allowed_geographies < parent.allowed_geographies,
                child.allowed_data_classes < parent.allowed_data_classes,
                child.parameter_constraints != parent.parameter_constraints,
                child.resource_prefixes != parent.resource_prefixes,
                child.max_per_action_usd < parent.max_per_action_usd,
                child.max_daily_spend_usd < parent.max_daily_spend_usd,
                child.max_total_spend_usd < parent.max_total_spend_usd,
            )
        )
        if not strict:
            raise AuthorizationError("child grant must narrow at least one dimension")

    def _store_grant(
        self,
        grant: CapabilityGrant,
        actor_id: str,
        event_type: str,
    ) -> None:
        self._grants[grant.grant_id] = grant
        self.ledger.append(
            event_type,
            actor_id,
            {
                "grant_id": grant.grant_id,
                "agent_id": grant.agent_id,
                "action_type": grant.action_type,
                "stage": grant.stage,
                "resource_prefixes": grant.resource_prefixes,
                "expires_at": grant.expires_at,
                "context_fingerprint": grant.context_fingerprint,
                "parameter_constraints": grant.parameter_constraints,
                "delegation_depth": grant.delegation_depth,
                "parent_grant_id": grant.parent_grant_id,
                "daily_budget_usd": grant.max_daily_spend_usd,
                "total_budget_usd": grant.max_total_spend_usd,
            },
            cell_id=grant.cell_id,
        )
        self._persist_state()

    def _require_grant(self, grant_id: str) -> CapabilityGrant:
        grant = self._grants.get(grant_id)
        if grant is None:
            raise PolicyConfigurationError("grant not found")
        return grant

    def _select_grant(self, intent: ActionIntent) -> Optional[CapabilityGrant]:
        candidates = [
            grant
            for grant in self._grants.values()
            if grant.active
            and grant.cell_id == intent.cell_id
            and grant.agent_id == intent.agent_id
            and grant.action_type == intent.action_type
            and not self._is_expired(grant.expires_at)
            and any(intent.resource.startswith(prefix) for prefix in grant.resource_prefixes)
        ]
        if not candidates:
            return None

        def specificity(grant: CapabilityGrant) -> tuple[int, int, float]:
            longest = max(
                len(prefix)
                for prefix in grant.resource_prefixes
                if intent.resource.startswith(prefix)
            )
            return longest, int(grant.stage), grant.issued_at.timestamp()

        return max(candidates, key=specificity)

    def _budget_violation(
        self,
        intent: ActionIntent,
        grant: CapabilityGrant,
        cell: VentureCellCharter,
    ) -> Optional[str]:
        amount = intent.amount_usd
        if amount == 0:
            return None
        day = utc_now().date().isoformat()
        if amount > grant.max_per_action_usd:
            return "grant_per_action_budget_exceeded"
        if (
            self._grant_daily_spend.get((grant.grant_id, day), Decimal("0")) + amount
            > grant.max_daily_spend_usd
        ):
            return "grant_daily_budget_exceeded"
        if self._grant_total_spend.get(grant.grant_id, Decimal("0")) + amount > grant.max_total_spend_usd:
            return "grant_total_budget_exceeded"
        if (
            self._cell_daily_spend.get((cell.cell_id, day), Decimal("0")) + amount
            > cell.max_daily_spend_usd
        ):
            return "cell_daily_budget_exceeded"
        if self._cell_total_spend.get(cell.cell_id, Decimal("0")) + amount > cell.max_total_spend_usd:
            return "cell_total_budget_exceeded"
        return None

    @staticmethod
    def _parameter_violation(
        intent: ActionIntent,
        grant: CapabilityGrant,
    ) -> Optional[str]:
        for path, allowed_values in grant.parameter_constraints.items():
            current: object = intent.payload
            for component in path.split("."):
                if not isinstance(current, Mapping) or component not in current:
                    return "required_parameter_missing"
                current = current[component]
            if not any(current == allowed for allowed in allowed_values):
                return "parameter_outside_grant"
        return None

    def _valid_approvers(self, intent: ActionIntent) -> frozenset[str]:
        fingerprint = intent.fingerprint()
        approvers = {
            approval.approver_id
            for approval in self._approvals.values()
            if approval.action_fingerprint == fingerprint
            and approval.policy_version == self.policy_version
            and approval.approver_id in self.human_authorities
            and not self._is_expired(approval.expires_at)
        }
        return frozenset(approvers)

    def _decision(
        self,
        intent: ActionIntent,
        disposition: PolicyDisposition,
        reason_codes: tuple[str, ...],
        definition: Optional[ActionDefinition] = None,
        grant: Optional[CapabilityGrant] = None,
        valid_approvals: int = 0,
    ) -> PolicyDecision:
        decision = PolicyDecision(
            action_id=intent.action_id,
            action_type=intent.action_type,
            disposition=disposition,
            reason_codes=reason_codes,
            policy_version=self.policy_version,
            risk_tier=definition.risk_tier if definition else None,
            grant_id=grant.grant_id if grant else None,
            required_human_approvals=(
                definition.required_human_approvals if definition else 0
            ),
            valid_human_approvals=valid_approvals,
        )
        self.ledger.append(
            "policy_decision",
            "policy-engine",
            {
                "intent_fingerprint": intent.fingerprint(),
                "action_type": intent.action_type,
                "resource": intent.resource,
                "disposition": disposition,
                "reason_codes": reason_codes,
                "risk_tier": decision.risk_tier,
                "grant_id": decision.grant_id,
                "required_human_approvals": decision.required_human_approvals,
                "valid_human_approvals": decision.valid_human_approvals,
                "policy_version": self.policy_version,
            },
            cell_id=intent.cell_id,
                action_id=intent.action_id,
            )
        return decision

    def _record_promotion_decision(
        self,
        actor_id: str,
        grant: CapabilityGrant,
        evidence: PromotionEvidence,
        evaluation: PromotionEvaluation,
        independent_review_id: str,
    ) -> None:
        self.ledger.append(
            "capability_promotion_decision",
            actor_id,
            {
                "grant_id": grant.grant_id,
                "from_stage": grant.stage,
                "to_stage": (
                    AutonomyStage(grant.stage + 1)
                    if grant.stage < AutonomyStage.SCALED_BOUNDED
                    else grant.stage
                ),
                "independent_review_id": independent_review_id,
                "evidence": evidence,
                "passed": evaluation.passed,
                "reasons": evaluation.reasons,
                "failure_upper_bound": evaluation.failure_upper_bound,
            },
            cell_id=grant.cell_id,
        )

    def _regress_grant(
        self,
        actor_id: str,
        grant_id: str,
        target_stage: AutonomyStage,
        reason: str,
    ) -> CapabilityGrant:
        grant = self._require_grant(grant_id)
        if target_stage >= grant.stage:
            raise PolicyConfigurationError("regression target must reduce authority")
        regressed = replace(grant, stage=target_stage)
        self._grants[grant_id] = regressed
        self.ledger.append(
            "capability_grant_regressed",
            actor_id,
            {
                "grant_id": grant_id,
                "from_stage": grant.stage,
                "to_stage": target_stage,
                "reason": reason,
            },
            cell_id=grant.cell_id,
        )
        self._persist_state()
        return regressed


__all__ = [
    "AuthorizationError",
    "PolicyConfigurationError",
    "PolicyEngine",
]
