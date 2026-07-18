"""Deny-by-default policy, evidence, audit, and reconstruction service.

The service is intentionally deterministic.  It never asks a language model
whether an action is permitted.  It records proposals and may authorize only
the bounded action classes proven by identity, contract, capability, evidence,
budget, approval, and kill-switch state.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable
from uuid import uuid4

from sqlalchemy.orm import Session

from .models import (
    ActionRequestRecord,
    AgentContractRecord,
    ApprovalRecord,
    AuditEventRecord,
    BudgetAccountRecord,
    CapabilityGrantRecord,
    ClaimRecord,
    EvidenceRecord,
    ExecutionRecord,
    GovernanceIdentity,
    KillSwitchRecord,
    PolicyDecisionRecord,
    VerificationRecord,
)


RISK_RANK = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}
FINAL_POLICY_DECISIONS = {
    "authorized",
    "human_execution_only",
    "denied",
    "held",
}
ACTIVE_EVIDENCE_STATUSES = {"verified"}


class GovernanceError(ValueError):
    """A fail-closed governance or record-integrity error."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def payload_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def json_safe(value: Any) -> Any:
    """Return a canonical JSON-compatible copy of ``value``."""

    return json.loads(json.dumps(value, default=str))


def model_dict(record: Any, fields: Iterable[str]) -> dict[str, Any]:
    return {field: getattr(record, field) for field in fields}


class GovernanceService:
    """Operate one authoritative governance transaction using ``session``."""

    evaluator = "deterministic_policy_v1"

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Registry and bootstrap
    # ------------------------------------------------------------------
    def register_identity(self, payload: dict[str, Any], actor_id: str) -> GovernanceIdentity:
        identity_id = payload["identity_id"]
        if self.session.get(GovernanceIdentity, identity_id):
            raise GovernanceError("identity already exists")
        record = GovernanceIdentity(
            identity_id=identity_id,
            identity_type=payload["identity_type"],
            display_name=payload["display_name"],
            venture_id=payload.get("venture_id"),
            role=payload["role"],
            active=payload.get("active", True),
            attributes=json_safe(payload.get("attributes", {})),
            expires_at=payload.get("expires_at"),
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "identity.registered", "identity", identity_id, payload)
        return record

    def register_contract(
        self, payload: dict[str, Any], actor_id: str
    ) -> AgentContractRecord:
        contract_id = payload["contract_id"]
        if self.session.get(AgentContractRecord, contract_id):
            raise GovernanceError("contract already exists")
        if not self.session.get(GovernanceIdentity, payload["subject_id"]):
            raise GovernanceError("contract subject identity does not exist")
        record = AgentContractRecord(
            contract_id=contract_id,
            subject_id=payload["subject_id"],
            venture_id=payload["venture_id"],
            mission=payload["mission"],
            allowed_actions=payload["allowed_actions"],
            prohibited_actions=payload.get("prohibited_actions", []),
            allowed_data_classes=payload.get("allowed_data_classes", ["public", "internal"]),
            owner_id=payload["owner_id"],
            version=payload.get("version", "1"),
            status=payload.get("status", "active"),
            expires_at=payload.get("expires_at"),
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "contract.registered", "contract", contract_id, payload)
        return record

    def grant_capability(
        self, payload: dict[str, Any], actor_id: str
    ) -> CapabilityGrantRecord:
        grant_id = payload["grant_id"]
        if self.session.get(CapabilityGrantRecord, grant_id):
            raise GovernanceError("capability grant already exists")
        if payload["max_risk_class"] not in RISK_RANK:
            raise GovernanceError("unknown risk class")
        if payload["granted_by"] != actor_id:
            raise GovernanceError("capability grantor must match authenticated actor")
        if not self.session.get(GovernanceIdentity, payload["subject_id"]):
            raise GovernanceError("capability subject identity does not exist")
        record = CapabilityGrantRecord(
            grant_id=grant_id,
            subject_id=payload["subject_id"],
            venture_id=payload["venture_id"],
            action_type=payload["action_type"],
            environments=payload["environments"],
            max_risk_class=payload["max_risk_class"],
            money_limit_minor=payload.get("money_limit_minor", 0),
            active=payload.get("active", True),
            granted_by=payload["granted_by"],
            expires_at=payload.get("expires_at"),
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "capability.granted", "capability", grant_id, payload)
        return record

    def set_budget(self, payload: dict[str, Any], actor_id: str) -> BudgetAccountRecord:
        existing = (
            self.session.query(BudgetAccountRecord)
            .filter_by(venture_id=payload["venture_id"], currency=payload["currency"])
            .one_or_none()
        )
        if existing:
            if payload["limit_minor"] < existing.reserved_minor + existing.spent_minor:
                raise GovernanceError("budget limit cannot fall below committed resources")
            existing.limit_minor = payload["limit_minor"]
            existing.status = payload.get("status", existing.status)
            existing.owner_id = payload["owner_id"]
            record = existing
            event_type = "budget.updated"
        else:
            record = BudgetAccountRecord(
                budget_id=payload["budget_id"],
                venture_id=payload["venture_id"],
                currency=payload["currency"],
                limit_minor=payload["limit_minor"],
                owner_id=payload["owner_id"],
                status=payload.get("status", "active"),
            )
            self.session.add(record)
            event_type = "budget.created"
        self.session.flush()
        self._audit(actor_id, event_type, "budget", record.budget_id, payload)
        return record

    # ------------------------------------------------------------------
    # Evidence plane
    # ------------------------------------------------------------------
    def create_claim(self, payload: dict[str, Any], actor_id: str) -> ClaimRecord:
        claim_id = payload["claim_id"]
        if self.session.get(ClaimRecord, claim_id):
            raise GovernanceError("claim already exists")
        record = ClaimRecord(
            claim_id=claim_id,
            venture_id=payload["venture_id"],
            statement=payload["statement"],
            claim_type=payload["claim_type"],
            status=payload.get("status", "hypothesis"),
            owner_id=payload["owner_id"],
            review_at=payload["review_at"],
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "claim.recorded", "claim", claim_id, payload)
        return record

    def record_evidence(self, payload: dict[str, Any], actor_id: str) -> EvidenceRecord:
        evidence_id = payload["evidence_id"]
        if payload["recorded_by"] != actor_id:
            raise GovernanceError("evidence recorder must match authenticated actor")
        if self.session.get(EvidenceRecord, evidence_id):
            raise GovernanceError("evidence already exists")
        claim = self.session.get(ClaimRecord, payload["claim_id"])
        if not claim or claim.venture_id != payload["venture_id"]:
            raise GovernanceError("evidence claim is missing or belongs to another venture")
        integrity = payload["integrity"]
        if payload.get("verification_status", "unverified") != "unverified" or payload.get(
            "verified_by"
        ):
            raise GovernanceError("new evidence must enter as unverified and use independent verification")
        record = EvidenceRecord(
            evidence_id=evidence_id,
            claim_id=payload["claim_id"],
            venture_id=payload["venture_id"],
            evidence_grade=payload["evidence_grade"],
            evidence_type=payload["evidence_type"],
            source=json_safe(payload["source"]),
            observed_at=payload["observed_at"],
            recorded_at=payload.get("recorded_at", utcnow()),
            recorded_by=payload["recorded_by"],
            scope=payload["scope"],
            content_ref=payload.get("content_ref"),
            summary=payload.get("summary"),
            verification_status=payload.get("verification_status", "unverified"),
            verified_by=payload.get("verified_by"),
            contradicts_evidence_ids=json_safe(payload.get("contradicts_evidence_ids", [])),
            limitations=json_safe(payload.get("limitations", [])),
            integrity_sha256=integrity["sha256"],
            custody_log_ref=integrity["custody_log_ref"],
            classification=payload["classification"],
            retention_policy_id=payload.get("retention_policy_id"),
            review_at=payload["review_at"],
            expires_at=payload.get("expires_at"),
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "evidence.recorded", "evidence", evidence_id, payload)
        return record

    def verify_evidence(
        self, evidence_id: str, verifier_id: str, status: str, reason: str
    ) -> EvidenceRecord:
        if status not in {"verified", "disputed", "invalid", "superseded"}:
            raise GovernanceError("unsupported verification status")
        record = self._required(EvidenceRecord, evidence_id, "evidence")
        self._active_human(verifier_id, "evidence verifier")
        if record.recorded_by == verifier_id:
            raise GovernanceError("evidence verification must be independent")
        record.verification_status = status
        record.verified_by = verifier_id
        self.session.flush()
        self._audit(
            verifier_id,
            "evidence.verified",
            "evidence",
            evidence_id,
            {"status": status, "reason": reason},
        )
        return record

    # ------------------------------------------------------------------
    # Action control plane
    # ------------------------------------------------------------------
    def create_action(self, payload: dict[str, Any], actor_id: str) -> ActionRequestRecord:
        if payload["requester_id"] != actor_id:
            raise GovernanceError("requester identity must match authenticated actor")
        if payload["risk_class"] not in RISK_RANK:
            raise GovernanceError("unknown risk class")
        request_hash = payload_hash(payload)
        existing = (
            self.session.query(ActionRequestRecord)
            .filter_by(idempotency_key=payload["idempotency_key"])
            .one_or_none()
        )
        if existing:
            if existing.request_hash != request_hash:
                raise GovernanceError("idempotency key was reused with different content")
            return existing
        if self.session.get(ActionRequestRecord, payload["action_id"]):
            raise GovernanceError("action id already exists")
        record = ActionRequestRecord(
            action_id=payload["action_id"],
            idempotency_key=payload["idempotency_key"],
            request_hash=request_hash,
            requester_id=payload["requester_id"],
            agent_contract_id=payload["agent_contract_id"],
            venture_id=payload["venture_id"],
            action_type=payload["action_type"],
            target=json_safe(payload["target"]),
            risk_class=payload["risk_class"],
            purpose=payload["purpose"],
            active_bottleneck_id=payload.get("active_bottleneck_id"),
            evidence_refs=json_safe(payload["evidence_refs"]),
            expected_preconditions=json_safe(payload["expected_preconditions"]),
            expected_postconditions=json_safe(payload["expected_postconditions"]),
            resource_impact=json_safe(payload["resource_impact"]),
            rollback_or_compensation=json_safe(payload["rollback_or_compensation"]),
            requested_at=payload["requested_at"],
            expires_at=payload["expires_at"],
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "action.proposed", "action", record.action_id, payload)
        self.evaluate_action(record.action_id, actor_id="policy-engine")
        return record

    def evaluate_action(self, action_id: str, actor_id: str) -> PolicyDecisionRecord:
        action = self._required(ActionRequestRecord, action_id, "action")
        if self.session.query(ExecutionRecord).filter_by(action_id=action.action_id).first():
            raise GovernanceError("executed action cannot be re-evaluated")
        now = utcnow()
        checks: dict[str, dict[str, Any]] = {}
        reasons: list[str] = []

        requested_at = aware(action.requested_at)
        expires_at = aware(action.expires_at)
        action_window_ok = bool(
            requested_at and expires_at and requested_at <= now < expires_at
        )
        checks["action_window"] = {
            "passed": action_window_ok,
            "requested_at": requested_at.isoformat() if requested_at else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }
        if not action_window_ok:
            reasons.append(
                "action_not_yet_valid"
                if requested_at and requested_at > now
                else "action_expired"
            )

        minimum_risk_class = self._minimum_risk_class(action)
        risk_class_ok = (
            RISK_RANK[action.risk_class] >= RISK_RANK[minimum_risk_class]
        )
        checks["risk_classification"] = {
            "passed": risk_class_ok,
            "declared": action.risk_class,
            "minimum": minimum_risk_class,
        }
        if not risk_class_ok:
            reasons.append("risk_class_understated")

        identity = self.session.get(GovernanceIdentity, action.requester_id)
        identity_ok = bool(
            identity
            and identity.active
            and (not identity.expires_at or aware(identity.expires_at) > now)
        )
        checks["identity"] = {"passed": identity_ok}
        if not identity_ok:
            reasons.append("missing_or_expired_identity")

        contract = self.session.get(AgentContractRecord, action.agent_contract_id)
        contract_ok = bool(
            contract
            and contract.subject_id == action.requester_id
            and contract.venture_id in {action.venture_id, "portfolio"}
            and contract.status == "active"
            and (not contract.expires_at or aware(contract.expires_at) > now)
            and self._action_allowed(action.action_type, contract.allowed_actions)
            and not self._action_allowed(action.action_type, contract.prohibited_actions)
        )
        checks["contract"] = {"passed": contract_ok}
        if not contract_ok:
            reasons.append("missing_or_invalid_agent_contract")

        classifications = set(action.resource_impact.get("data_classifications", []))
        data_scope_ok = bool(contract and classifications <= set(contract.allowed_data_classes))
        checks["data_scope"] = {"passed": data_scope_ok, "requested": sorted(classifications)}
        if not data_scope_ok:
            reasons.append("data_classification_outside_contract")

        environment = action.target.get("environment")
        money_minor = int(action.resource_impact.get("money_minor", 0))
        grant = self._matching_grant(action, environment, money_minor, now)
        capability_ok = grant is not None
        checks["capability"] = {"passed": capability_ok, "grant_id": getattr(grant, "grant_id", None)}
        if not capability_ok:
            reasons.append("missing_capability")

        kill_switches = self._active_kill_switches(action)
        checks["kill_switch"] = {
            "passed": not kill_switches,
            "active_switches": [item.switch_id for item in kill_switches],
        }
        if kill_switches:
            reasons.append("venture_or_portfolio_kill_switch_active")

        evidence, evidence_errors = self._action_evidence(action, now)
        checks["evidence"] = {
            "passed": not evidence_errors,
            "records": [item.evidence_id for item in evidence],
        }
        reasons.extend(evidence_errors)

        budget = self._budget(action)
        budget_ok = self._budget_allows(
            budget,
            money_minor,
            already_reserved=action.budget_reserved,
        )
        checks["budget"] = {
            "passed": budget_ok,
            "budget_id": getattr(budget, "budget_id", None),
            "money_minor": money_minor,
        }
        if not budget_ok:
            reasons.append("budget_exceeded_or_missing")

        rollback = action.rollback_or_compensation
        rollback_required = action.risk_class in {"R2", "R3"}
        rollback_ok = not rollback_required or bool(
            rollback.get("available") and rollback.get("plan") and rollback.get("owner_id")
        )
        checks["rollback"] = {"passed": rollback_ok, "required": rollback_required}
        if not rollback_ok:
            reasons.append("missing_rollback_for_R2_or_R3_when_rollback_is_required")

        approvals = self._valid_approvals(action, now)
        denied = any(item.decision == "deny" for item in approvals)
        required_authorities = self._required_authorities(action)
        approved_authorities = {
            item.authority for item in approvals if item.decision == "approve"
        }
        approving_identities = {
            item.approver_id for item in approvals if item.decision == "approve"
        }
        dual_control_required = action.risk_class in {"R3", "R4"}
        dual_control_ok = not dual_control_required or len(approving_identities) >= 2
        approvals_ok = required_authorities <= approved_authorities and dual_control_ok
        checks["approvals"] = {
            "passed": approvals_ok and not denied,
            "required": sorted(required_authorities),
            "present": sorted(approved_authorities),
            "distinct_approvers": len(approving_identities),
            "dual_control_required": dual_control_required,
            "denied": denied,
        }

        base_checks = [
            action_window_ok,
            risk_class_ok,
            identity_ok,
            contract_ok,
            data_scope_ok,
            capability_ok,
            not kill_switches,
            not evidence_errors,
            budget_ok,
            rollback_ok,
        ]
        if denied:
            decision = "denied"
            reasons.append("approval_denied")
        elif not all(base_checks):
            decision = "held"
        elif not approvals_ok:
            decision = "requires_human_approval"
            reasons.append(
                "dual_control_missing"
                if required_authorities <= approved_authorities and not dual_control_ok
                else "required_human_approval_missing"
            )
        elif action.risk_class == "R4":
            decision = "human_execution_only"
            reasons.append("R4_autonomous_execution_prohibited")
        else:
            decision = "authorized"
            reasons.append("all_required_controls_satisfied")

        record = PolicyDecisionRecord(
            decision_id=str(uuid4()),
            action_id=action.action_id,
            decision=decision,
            reasons=list(dict.fromkeys(reasons)),
            checks=checks,
            evaluator=self.evaluator,
            created_at=utcnow(),
        )
        self.session.add(record)
        action.status = decision
        if decision in {"authorized", "human_execution_only"}:
            self._reserve_budget(action, budget, money_minor)
        else:
            self._release_budget_reservation(action, money_minor)
        self.session.flush()
        self._audit(
            actor_id,
            "policy.evaluated",
            "action",
            action.action_id,
            {
                "policy_decision_id": record.decision_id,
                "decision": decision,
                "reasons": record.reasons,
                "checks": checks,
            },
        )
        return record

    def record_approval(self, payload: dict[str, Any], actor_id: str) -> ApprovalRecord:
        if payload["approver_id"] != actor_id:
            raise GovernanceError("approver identity must match authenticated actor")
        action = self._required(ActionRequestRecord, payload["action_id"], "action")
        if self.session.query(ExecutionRecord).filter_by(action_id=action.action_id).first():
            raise GovernanceError("approval cannot be added after execution")
        if aware(action.expires_at) <= utcnow():
            raise GovernanceError("approval cannot be added to an expired action")
        identity = self._active_human(actor_id, "approver identity")
        if action.requester_id == actor_id:
            raise GovernanceError("requester cannot approve the same action")
        authorities = set((identity.attributes or {}).get("authorities", []))
        if payload["authority"] not in authorities:
            raise GovernanceError("approver lacks the claimed authority")
        if payload["decision"] not in {"approve", "deny"}:
            raise GovernanceError("approval decision must be approve or deny")
        if payload.get("expires_at") and aware(payload["expires_at"]) <= utcnow():
            raise GovernanceError("approval expiration must be in the future")
        if self.session.get(ApprovalRecord, payload["approval_id"]):
            raise GovernanceError("approval id already exists")
        existing = (
            self.session.query(ApprovalRecord)
            .filter_by(
                action_id=action.action_id,
                approver_id=actor_id,
                authority=payload["authority"],
            )
            .one_or_none()
        )
        if existing:
            raise GovernanceError("approval records are immutable")
        record = ApprovalRecord(
            approval_id=payload["approval_id"],
            action_id=action.action_id,
            approver_id=actor_id,
            authority=payload["authority"],
            decision=payload["decision"],
            reason=payload["reason"],
            expires_at=payload.get("expires_at"),
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "approval.recorded", "action", action.action_id, payload)
        self.evaluate_action(action.action_id, actor_id="policy-engine")
        return record

    # ------------------------------------------------------------------
    # Human-recorded execution and independent verification
    # ------------------------------------------------------------------
    def record_execution(self, payload: dict[str, Any], actor_id: str) -> ExecutionRecord:
        action = self._required(ActionRequestRecord, payload["action_id"], "action")
        if self.session.query(ExecutionRecord).filter_by(action_id=action.action_id).first():
            raise GovernanceError("execution record already exists")
        decision = self.evaluate_action(action.action_id, actor_id="policy-engine")
        if decision.decision not in {"authorized", "human_execution_only"}:
            raise GovernanceError("action failed immediate policy re-evaluation")
        if payload["executor_id"] != actor_id:
            raise GovernanceError("executor identity must match authenticated actor")
        self._active_human(actor_id, "executor")
        if action.risk_class in {"R3", "R4"}:
            approver_ids = {
                item.approver_id
                for item in self._valid_approvals(action, utcnow())
                if item.decision == "approve"
            }
            if actor_id == action.requester_id or actor_id in approver_ids:
                raise GovernanceError(
                    "R3 and R4 execution must be independent from requester and approvers"
                )
        if self.session.get(ExecutionRecord, payload["execution_id"]):
            raise GovernanceError("execution id already exists")
        executed_at = aware(payload["executed_at"])
        now = utcnow()
        if (
            not executed_at
            or executed_at < aware(action.requested_at)
            or executed_at >= aware(action.expires_at)
            or executed_at > now
        ):
            raise GovernanceError(
                "execution time must be inside the authorized window and not in the future"
            )
        record = ExecutionRecord(
            execution_id=payload["execution_id"],
            action_id=action.action_id,
            executor_id=actor_id,
            external_ref=payload["external_ref"],
            result=json_safe(payload["result"]),
            status=payload["status"],
            executed_at=payload["executed_at"],
        )
        self.session.add(record)
        planned_minor = int(action.resource_impact.get("money_minor", 0))
        actual_minor = int(payload["result"].get("actual_money_minor", planned_minor))
        if actual_minor < 0 or actual_minor > planned_minor:
            raise GovernanceError("actual spend must remain within the authorized reservation")
        if action.budget_reserved and planned_minor:
            budget = self._budget(action)
            if not budget or budget.reserved_minor < planned_minor:
                raise GovernanceError("budget reservation cannot be reconciled")
            budget.reserved_minor -= planned_minor
            budget.spent_minor += actual_minor
            action.budget_reserved = False
        action.status = "executed_unverified"
        self.session.flush()
        self._audit(actor_id, "execution.recorded", "action", action.action_id, payload)
        return record

    def record_verification(
        self, payload: dict[str, Any], actor_id: str
    ) -> VerificationRecord:
        action = self._required(ActionRequestRecord, payload["action_id"], "action")
        execution = (
            self.session.query(ExecutionRecord).filter_by(action_id=action.action_id).one_or_none()
        )
        if not execution:
            raise GovernanceError("execution must be recorded before verification")
        if payload["verifier_id"] != actor_id:
            raise GovernanceError("verifier identity must match authenticated actor")
        self._active_human(actor_id, "outcome verifier")
        if actor_id in {execution.executor_id, action.requester_id}:
            raise GovernanceError("outcome verification must be independent")
        if self.session.query(VerificationRecord).filter_by(action_id=action.action_id).first():
            raise GovernanceError("verification record already exists")
        if self.session.get(VerificationRecord, payload["verification_id"]):
            raise GovernanceError("verification id already exists")
        evidence = self._evidence_by_ids(payload["evidence_refs"])
        if len(evidence) != len(set(payload["evidence_refs"])):
            raise GovernanceError("verification references missing evidence")
        if any(
            item.venture_id not in {action.venture_id, "portfolio"}
            for item in evidence
        ):
            raise GovernanceError("verification evidence belongs to another venture")
        now = utcnow()
        verified_at = aware(payload["verified_at"])
        if not verified_at or verified_at < aware(execution.executed_at) or verified_at > now:
            raise GovernanceError("verification time must follow execution and not be in the future")
        if payload["status"] == "verified":
            expected = set(action.expected_postconditions)
            if not expected <= set(payload["postconditions"]) or not all(
                payload["postconditions"].get(item) is True for item in expected
            ):
                raise GovernanceError("verified outcome must satisfy every expected postcondition")
            for item in evidence:
                if item.verification_status != "verified":
                    raise GovernanceError("verified outcome requires independently verified evidence")
                if aware(item.review_at) <= now or (
                    item.expires_at and aware(item.expires_at) <= now
                ):
                    raise GovernanceError("verified outcome requires current evidence")
        record = VerificationRecord(
            verification_id=payload["verification_id"],
            action_id=action.action_id,
            verifier_id=actor_id,
            status=payload["status"],
            postconditions=json_safe(payload["postconditions"]),
            evidence_refs=json_safe(payload["evidence_refs"]),
            verified_at=payload["verified_at"],
        )
        self.session.add(record)
        action.status = "verified" if payload["status"] == "verified" else "verification_failed"
        self.session.flush()
        self._audit(actor_id, "outcome.verified", "action", action.action_id, payload)
        return record

    # ------------------------------------------------------------------
    # Incident controls
    # ------------------------------------------------------------------
    def activate_kill_switch(
        self, payload: dict[str, Any], actor_id: str
    ) -> KillSwitchRecord:
        if self.session.get(KillSwitchRecord, payload["switch_id"]):
            raise GovernanceError("kill switch id already exists")
        identity = self._active_human(actor_id, "incident authority")
        authorities = set((identity.attributes or {}).get("authorities", []))
        if not {"security_authority", "system_governor"} & authorities:
            raise GovernanceError("kill-switch activation requires incident authority")
        record = KillSwitchRecord(
            switch_id=payload["switch_id"],
            scope_type=payload["scope_type"],
            scope_id=payload["scope_id"],
            active=True,
            reason=payload["reason"],
            activated_by=actor_id,
        )
        self.session.add(record)
        self.session.flush()
        self._audit(actor_id, "kill_switch.activated", "kill_switch", record.switch_id, payload)
        return record

    def release_kill_switch(
        self, switch_id: str, actor_id: str, reason: str
    ) -> KillSwitchRecord:
        record = self._required(KillSwitchRecord, switch_id, "kill switch")
        if not record.active:
            raise GovernanceError("kill switch is already released")
        identity = self._active_human(actor_id, "identity")
        authorities = set((identity.attributes or {}).get("authorities", []))
        if "system_governor" not in authorities:
            raise GovernanceError("kill-switch release requires system governor authority")
        record.active = False
        record.released_by = actor_id
        record.released_reason = reason
        record.released_at = utcnow()
        self.session.flush()
        self._audit(
            actor_id,
            "kill_switch.released",
            "kill_switch",
            switch_id,
            {"reason": reason},
        )
        return record

    # ------------------------------------------------------------------
    # Reconstruction and assurance
    # ------------------------------------------------------------------
    def reconstruct_action(self, action_id: str) -> dict[str, Any]:
        action = self._required(ActionRequestRecord, action_id, "action")
        decisions = (
            self.session.query(PolicyDecisionRecord)
            .filter_by(action_id=action_id)
            .order_by(PolicyDecisionRecord.created_at, PolicyDecisionRecord.decision_id)
            .all()
        )
        approvals = self.session.query(ApprovalRecord).filter_by(action_id=action_id).all()
        evidence = self._evidence_by_ids(action.evidence_refs)
        execution = self.session.query(ExecutionRecord).filter_by(action_id=action_id).one_or_none()
        verification = (
            self.session.query(VerificationRecord).filter_by(action_id=action_id).one_or_none()
        )
        audit = (
            self.session.query(AuditEventRecord)
            .filter_by(aggregate_type="action", aggregate_id=action_id)
            .order_by(AuditEventRecord.sequence)
            .all()
        )
        return {
            "action": self._action_view(action),
            "evidence": [self._evidence_view(item) for item in evidence],
            "approvals": [
                model_dict(
                    item,
                    [
                        "approval_id",
                        "approver_id",
                        "authority",
                        "decision",
                        "reason",
                        "created_at",
                        "expires_at",
                    ],
                )
                for item in approvals
            ],
            "policy_decisions": [
                model_dict(
                    item,
                    ["decision_id", "decision", "reasons", "checks", "evaluator", "created_at"],
                )
                for item in decisions
            ],
            "execution": (
                model_dict(
                    execution,
                    [
                        "execution_id",
                        "executor_id",
                        "external_ref",
                        "result",
                        "status",
                        "executed_at",
                    ],
                )
                if execution
                else None
            ),
            "verification": (
                model_dict(
                    verification,
                    [
                        "verification_id",
                        "verifier_id",
                        "status",
                        "postconditions",
                        "evidence_refs",
                        "verified_at",
                    ],
                )
                if verification
                else None
            ),
            "audit_events": [self._audit_view(item) for item in audit],
            "audit_chain_valid": self.verify_audit_chain(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "control_plane": "AG1_vertical_slice_candidate",
            "evidence_plane": "AG2_vertical_slice_candidate",
            "external_execution": "human_record_only",
            "autonomous_external_authority": "none",
            "identities": self.session.query(GovernanceIdentity).count(),
            "active_contracts": self.session.query(AgentContractRecord).filter_by(status="active").count(),
            "active_grants": self.session.query(CapabilityGrantRecord).filter_by(active=True).count(),
            "claims": self.session.query(ClaimRecord).count(),
            "evidence_records": self.session.query(EvidenceRecord).count(),
            "actions": self.session.query(ActionRequestRecord).count(),
            "pending_approvals": self.session.query(ActionRequestRecord)
            .filter_by(status="requires_human_approval")
            .count(),
            "active_kill_switches": self.session.query(KillSwitchRecord)
            .filter_by(active=True)
            .count(),
            "audit_chain_valid": self.verify_audit_chain(),
        }

    def verify_audit_chain(self) -> bool:
        previous = "0" * 64
        events = self.session.query(AuditEventRecord).order_by(AuditEventRecord.sequence).all()
        for event in events:
            body = {
                "event_id": event.event_id,
                "actor_id": event.actor_id,
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "payload": event.payload,
                "created_at": aware(event.created_at).isoformat(),
            }
            expected = hashlib.sha256(
                (previous + canonical_json(body)).encode("utf-8")
            ).hexdigest()
            if event.previous_hash != previous or event.event_hash != expected:
                return False
            previous = event.event_hash
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _audit(
        self,
        actor_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> AuditEventRecord:
        last = (
            self.session.query(AuditEventRecord)
            .order_by(AuditEventRecord.sequence.desc())
            .first()
        )
        previous_hash = last.event_hash if last else "0" * 64
        created_at = utcnow()
        event_id = str(uuid4())
        body = {
            "event_id": event_id,
            "actor_id": actor_id,
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "created_at": created_at.isoformat(),
        }
        event_hash = hashlib.sha256(
            (previous_hash + canonical_json(body)).encode("utf-8")
        ).hexdigest()
        event = AuditEventRecord(
            event_id=event_id,
            actor_id=actor_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=json_safe(payload),
            previous_hash=previous_hash,
            event_hash=event_hash,
            created_at=created_at,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _required(self, model: Any, record_id: str, label: str) -> Any:
        record = self.session.get(model, record_id)
        if not record:
            raise GovernanceError(f"{label} not found")
        return record

    def _active_human(self, identity_id: str, label: str) -> GovernanceIdentity:
        identity = self._required(GovernanceIdentity, identity_id, label)
        if (
            not identity.active
            or identity.identity_type != "human"
            or (identity.expires_at and aware(identity.expires_at) <= utcnow())
        ):
            raise GovernanceError(f"{label} must be an active human identity")
        return identity

    @staticmethod
    def _action_allowed(action_type: str, patterns: Iterable[str]) -> bool:
        return "*" in patterns or action_type in patterns

    def _matching_grant(
        self,
        action: ActionRequestRecord,
        environment: str,
        money_minor: int,
        now: datetime,
    ) -> CapabilityGrantRecord | None:
        grants = (
            self.session.query(CapabilityGrantRecord)
            .filter_by(subject_id=action.requester_id, active=True)
            .all()
        )
        for grant in grants:
            if grant.venture_id not in {action.venture_id, "portfolio"}:
                continue
            if grant.action_type not in {action.action_type, "*"}:
                continue
            if environment not in grant.environments:
                continue
            if RISK_RANK[grant.max_risk_class] < RISK_RANK[action.risk_class]:
                continue
            if money_minor > grant.money_limit_minor:
                continue
            if grant.expires_at and aware(grant.expires_at) <= now:
                continue
            return grant
        return None

    def _active_kill_switches(self, action: ActionRequestRecord) -> list[KillSwitchRecord]:
        switches = self.session.query(KillSwitchRecord).filter_by(active=True).all()
        matched = []
        for switch in switches:
            if switch.scope_type == "portfolio":
                matched.append(switch)
            elif switch.scope_type == "venture" and switch.scope_id == action.venture_id:
                matched.append(switch)
            elif switch.scope_type == "identity" and switch.scope_id == action.requester_id:
                matched.append(switch)
            elif switch.scope_type == "action_type" and switch.scope_id == action.action_type:
                matched.append(switch)
        return matched

    def _action_evidence(
        self, action: ActionRequestRecord, now: datetime
    ) -> tuple[list[EvidenceRecord], list[str]]:
        evidence = self._evidence_by_ids(action.evidence_refs)
        errors: list[str] = []
        if len(evidence) != len(set(action.evidence_refs)):
            errors.append("missing_gate_evidence")
            return evidence, errors
        for item in evidence:
            if item.venture_id not in {action.venture_id, "portfolio"}:
                errors.append("cross_venture_evidence_scope_violation")
            if aware(item.review_at) <= now or (
                item.expires_at and aware(item.expires_at) <= now
            ):
                errors.append("stale_evidence")
            if action.risk_class in {"R2", "R3", "R4"} and (
                item.verification_status not in ACTIVE_EVIDENCE_STATUSES
            ):
                errors.append("unverified_evidence_for_consequential_action")
            if item.verification_status in {"invalid", "superseded"}:
                errors.append("invalid_or_superseded_evidence")
        return evidence, list(dict.fromkeys(errors))

    def _evidence_by_ids(self, ids: Iterable[str]) -> list[EvidenceRecord]:
        unique = list(dict.fromkeys(ids))
        if not unique:
            return []
        return self.session.query(EvidenceRecord).filter(EvidenceRecord.evidence_id.in_(unique)).all()

    def _budget(self, action: ActionRequestRecord) -> BudgetAccountRecord | None:
        currency = action.resource_impact.get("currency")
        return (
            self.session.query(BudgetAccountRecord)
            .filter_by(venture_id=action.venture_id, currency=currency, status="active")
            .one_or_none()
        )

    @staticmethod
    def _budget_allows(
        budget: BudgetAccountRecord | None,
        money_minor: int,
        *,
        already_reserved: bool = False,
    ) -> bool:
        if money_minor == 0:
            return True
        if not budget:
            return False
        available = budget.limit_minor - budget.reserved_minor - budget.spent_minor
        if already_reserved:
            available += money_minor
        return available >= money_minor

    def _reserve_budget(
        self,
        action: ActionRequestRecord,
        budget: BudgetAccountRecord | None,
        money_minor: int,
    ) -> None:
        if action.budget_reserved or money_minor == 0:
            return
        if not budget:
            raise GovernanceError("authorized action is missing its budget")
        budget.reserved_minor += money_minor
        action.budget_reserved = True

    def _release_budget_reservation(
        self,
        action: ActionRequestRecord,
        money_minor: int,
    ) -> None:
        if not action.budget_reserved or money_minor == 0:
            return
        currency = action.resource_impact.get("currency")
        budget = (
            self.session.query(BudgetAccountRecord)
            .filter_by(venture_id=action.venture_id, currency=currency)
            .one_or_none()
        )
        if not budget or budget.reserved_minor < money_minor:
            raise GovernanceError("budget reservation cannot be released safely")
        budget.reserved_minor -= money_minor
        action.budget_reserved = False

    def _valid_approvals(
        self, action: ActionRequestRecord, now: datetime
    ) -> list[ApprovalRecord]:
        approvals = self.session.query(ApprovalRecord).filter_by(action_id=action.action_id).all()
        valid: list[ApprovalRecord] = []
        for item in approvals:
            if item.expires_at and aware(item.expires_at) <= now:
                continue
            identity = self.session.get(GovernanceIdentity, item.approver_id)
            if (
                not identity
                or not identity.active
                or identity.identity_type != "human"
                or (identity.expires_at and aware(identity.expires_at) <= now)
                or item.authority
                not in set((identity.attributes or {}).get("authorities", []))
            ):
                continue
            valid.append(item)
        return valid

    @staticmethod
    def _minimum_risk_class(action: ActionRequestRecord) -> str:
        """Derive a deterministic risk floor that requester labels cannot lower."""

        minimum = "R0"

        def raise_to(candidate: str) -> None:
            nonlocal minimum
            if RISK_RANK[candidate] > RISK_RANK[minimum]:
                minimum = candidate

        environment = str(action.target.get("environment", "")).lower()
        if environment == "sandbox":
            raise_to("R1")
        elif environment in {"staging", "external"}:
            raise_to("R2")
        elif environment == "production":
            raise_to("R3")

        impact = action.resource_impact or {}
        classifications = set(impact.get("data_classifications", []))
        if classifications & {"restricted", "regulated"}:
            raise_to("R3")
        elif "confidential" in classifications:
            raise_to("R2")

        relationship_risk = impact.get("relationship_risk")
        if relationship_risk == "high":
            raise_to("R3")
        elif relationship_risk == "medium":
            raise_to("R2")
        if int(impact.get("money_minor", 0)) > 0:
            raise_to("R2")

        action_type = action.action_type.lower()
        irreversible = (
            "sign_contract",
            "contract_sign",
            "transfer_funds",
            "fund_transfer",
            "issue_equity",
            "equity_issue",
            "incorporate",
            "dissolve",
            "legal_filing",
            "file_legal",
            "delete_critical",
            "launch_regulated",
            "regulated_launch",
            "open_bank",
            "close_bank",
            "assume_debt",
            "hire",
            "terminate",
        )
        high_consequence = (
            "material_spend",
            "deploy",
            "production",
            "credential",
            "secret",
            "privileged",
            "personal_data",
            "restricted_data",
            "regulated_data",
            "data_export",
            "public_claim",
            "price_change",
            "customer_access",
            "legal",
            "license",
            "regulated",
            "compensation",
        )
        bounded_external = (
            "publish",
            "send",
            "message",
            "campaign",
            "feature_flag",
            "vendor_account",
            "external",
        )
        if any(token in action_type for token in irreversible):
            raise_to("R4")
        elif any(token in action_type for token in high_consequence):
            raise_to("R3")
        elif any(token in action_type for token in bounded_external):
            raise_to("R2")
        return minimum

    def _required_authorities(self, action: ActionRequestRecord) -> set[str]:
        if action.risk_class in {"R0", "R1"}:
            return set()
        if action.risk_class == "R2":
            return {"venture_sponsor"}
        domain = self._domain_authority(action.action_type)
        required = {"designated_human"}
        if domain:
            required.add(domain)
        if action.risk_class == "R4" and not domain:
            required.add("system_governor")
        return required

    @staticmethod
    def _domain_authority(action_type: str) -> str | None:
        lowered = action_type.lower()
        domains = {
            "legal_authority": ("contract", "legal", "license", "filing", "regulated"),
            "financial_authority": ("fund", "payment", "spend", "bank", "debt", "equity"),
            "security_authority": ("deploy", "production", "credential", "secret", "privileged"),
            "privacy_authority": ("personal_data", "restricted_data", "data_export"),
            "human_resources_authority": ("hire", "terminate", "compensation"),
            "system_governor": ("venture_create", "venture_retire", "constitution", "risk_limit"),
        }
        for authority, needles in domains.items():
            if any(needle in lowered for needle in needles):
                return authority
        return None

    @staticmethod
    def _action_view(action: ActionRequestRecord) -> dict[str, Any]:
        return model_dict(
            action,
            [
                "action_id",
                "idempotency_key",
                "requester_id",
                "agent_contract_id",
                "venture_id",
                "action_type",
                "target",
                "risk_class",
                "purpose",
                "active_bottleneck_id",
                "evidence_refs",
                "expected_preconditions",
                "expected_postconditions",
                "resource_impact",
                "rollback_or_compensation",
                "status",
                "requested_at",
                "expires_at",
            ],
        )

    @staticmethod
    def _evidence_view(record: EvidenceRecord) -> dict[str, Any]:
        return model_dict(
            record,
            [
                "evidence_id",
                "claim_id",
                "venture_id",
                "evidence_grade",
                "evidence_type",
                "source",
                "observed_at",
                "recorded_at",
                "recorded_by",
                "scope",
                "content_ref",
                "summary",
                "verification_status",
                "verified_by",
                "contradicts_evidence_ids",
                "limitations",
                "integrity_sha256",
                "custody_log_ref",
                "classification",
                "review_at",
                "expires_at",
            ],
        )

    @staticmethod
    def _audit_view(record: AuditEventRecord) -> dict[str, Any]:
        return model_dict(
            record,
            [
                "sequence",
                "event_id",
                "actor_id",
                "event_type",
                "payload",
                "previous_hash",
                "event_hash",
                "created_at",
            ],
        )


__all__ = [
    "GovernanceError",
    "GovernanceService",
    "RISK_RANK",
    "canonical_json",
    "payload_hash",
    "utcnow",
]
