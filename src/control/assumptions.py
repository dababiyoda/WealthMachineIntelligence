"""Versioned assumptions linked to external or assurance evidence references."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional

from .evidence import EvidenceLedger
from .models import utc_now
from .policy_engine import AuthorizationError, PolicyConfigurationError


class EvidenceLane(str, Enum):
    VENTURE_VIABILITY = "venture_viability"
    CONTROL_ASSURANCE = "control_assurance"
    INTERNAL_CONTEXT = "internal_context"


class EvidenceOrigin(str, Enum):
    EXTERNAL_SYSTEM = "external_system"
    HUMAN_REVIEW = "human_review"
    INTERNAL_SIMULATION = "internal_simulation"


class AssumptionStatus(str, Enum):
    OPEN = "open"
    TESTING = "testing"
    VALIDATED = "validated"
    INVALIDATED = "invalidated"
    RETIRED = "retired"


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    lane: EvidenceLane
    origin: EvidenceOrigin
    source_reference: str
    content_digest: str
    observed_at: datetime
    description: str = ""


@dataclass(frozen=True)
class AssumptionRecord:
    assumption_id: str
    cell_id: str
    statement: str
    why_it_matters: str
    cheapest_decisive_test: str
    consequence_if_false: str
    test_deadline: datetime
    created_by: str
    status: AssumptionStatus = AssumptionStatus.OPEN
    evidence_ids: tuple[str, ...] = ()
    version: int = 1
    updated_at: datetime = field(default_factory=utc_now)


class AssumptionRegister:
    """Maintain an auditable assumption lifecycle without confidence shortcuts."""

    def __init__(
        self,
        ledger: EvidenceLedger,
        *,
        independent_verifiers: Iterable[str],
    ) -> None:
        self.ledger = ledger
        self.independent_verifiers = frozenset(independent_verifiers)
        self._assumptions: dict[str, AssumptionRecord] = {}
        self._evidence: dict[str, EvidenceReference] = {}
        self._lock = threading.RLock()

    def get(self, assumption_id: str) -> Optional[AssumptionRecord]:
        return self._assumptions.get(assumption_id)

    def register(self, actor_id: str, assumption: AssumptionRecord) -> AssumptionRecord:
        if assumption.status is not AssumptionStatus.OPEN or assumption.version != 1:
            raise PolicyConfigurationError("new assumptions must begin open at version one")
        if actor_id != assumption.created_by:
            raise AuthorizationError("the registering actor must be the assumption author")
        self._require_aware(assumption.test_deadline)
        if not all(
            (
                assumption.assumption_id,
                assumption.cell_id,
                assumption.statement,
                assumption.why_it_matters,
                assumption.cheapest_decisive_test,
                assumption.consequence_if_false,
            )
        ):
            raise PolicyConfigurationError("assumption fields cannot be empty")
        with self._lock:
            if assumption.assumption_id in self._assumptions:
                raise PolicyConfigurationError("assumption already exists")
            self._assumptions[assumption.assumption_id] = assumption
            self.ledger.append(
                "assumption_registered",
                actor_id,
                {
                    "assumption_id": assumption.assumption_id,
                    "statement": assumption.statement,
                    "why_it_matters": assumption.why_it_matters,
                    "cheapest_decisive_test": assumption.cheapest_decisive_test,
                    "consequence_if_false": assumption.consequence_if_false,
                    "test_deadline": assumption.test_deadline,
                    "version": assumption.version,
                },
                cell_id=assumption.cell_id,
            )
            return assumption

    def add_evidence(
        self,
        actor_id: str,
        assumption_id: str,
        evidence: EvidenceReference,
    ) -> AssumptionRecord:
        self._require_aware(evidence.observed_at)
        if not evidence.evidence_id or not evidence.source_reference or not evidence.content_digest:
            raise PolicyConfigurationError("evidence requires id, source reference, and digest")
        with self._lock:
            assumption = self._require_assumption(assumption_id)
            if evidence.evidence_id in self._evidence:
                raise PolicyConfigurationError("evidence id already exists")
            if assumption.status in {
                AssumptionStatus.VALIDATED,
                AssumptionStatus.INVALIDATED,
                AssumptionStatus.RETIRED,
            }:
                raise PolicyConfigurationError("terminal assumptions cannot accept new evidence")
            self._evidence[evidence.evidence_id] = evidence
            updated = replace(
                assumption,
                evidence_ids=assumption.evidence_ids + (evidence.evidence_id,),
                version=assumption.version + 1,
                updated_at=utc_now(),
            )
            self._assumptions[assumption_id] = updated
            self.ledger.append(
                "assumption_evidence_linked",
                actor_id,
                {
                    "assumption_id": assumption_id,
                    "evidence_id": evidence.evidence_id,
                    "lane": evidence.lane,
                    "origin": evidence.origin,
                    "source_reference": evidence.source_reference,
                    "content_digest": evidence.content_digest,
                    "observed_at": evidence.observed_at,
                    "version": updated.version,
                },
                cell_id=assumption.cell_id,
            )
            return updated

    def transition(
        self,
        actor_id: str,
        assumption_id: str,
        status: AssumptionStatus,
        rationale: str,
        *,
        verifier_id: Optional[str] = None,
    ) -> AssumptionRecord:
        if not rationale:
            raise PolicyConfigurationError("transition rationale is required")
        with self._lock:
            assumption = self._require_assumption(assumption_id)
            if assumption.status in {
                AssumptionStatus.VALIDATED,
                AssumptionStatus.INVALIDATED,
                AssumptionStatus.RETIRED,
            }:
                raise PolicyConfigurationError("terminal assumptions cannot transition")
            if status is AssumptionStatus.OPEN:
                raise PolicyConfigurationError("a transition cannot return to open")
            if status in {AssumptionStatus.VALIDATED, AssumptionStatus.INVALIDATED}:
                if verifier_id not in self.independent_verifiers:
                    raise AuthorizationError("an independent verifier is required")
                if verifier_id == assumption.created_by:
                    raise AuthorizationError("the author cannot verify the assumption")
                evidence = [self._evidence[item] for item in assumption.evidence_ids]
                if not any(
                    item.origin
                    in {EvidenceOrigin.EXTERNAL_SYSTEM, EvidenceOrigin.HUMAN_REVIEW}
                    for item in evidence
                ):
                    raise AuthorizationError(
                        "internal simulation alone cannot validate or invalidate an assumption"
                    )
            if status is AssumptionStatus.RETIRED and actor_id not in self.independent_verifiers:
                raise AuthorizationError("retirement requires an independent verifier")

            updated = replace(
                assumption,
                status=status,
                version=assumption.version + 1,
                updated_at=utc_now(),
            )
            self._assumptions[assumption_id] = updated
            self.ledger.append(
                "assumption_transitioned",
                actor_id,
                {
                    "assumption_id": assumption_id,
                    "from_status": assumption.status,
                    "to_status": status,
                    "rationale": rationale,
                    "verifier_id": verifier_id,
                    "evidence_ids": assumption.evidence_ids,
                    "version": updated.version,
                },
                cell_id=assumption.cell_id,
            )
            return updated

    def _require_assumption(self, assumption_id: str) -> AssumptionRecord:
        assumption = self._assumptions.get(assumption_id)
        if assumption is None:
            raise PolicyConfigurationError("assumption not found")
        return assumption

    @staticmethod
    def _require_aware(timestamp: datetime) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise PolicyConfigurationError("timestamps must be timezone-aware")


__all__ = [
    "AssumptionRecord",
    "AssumptionRegister",
    "AssumptionStatus",
    "EvidenceLane",
    "EvidenceOrigin",
    "EvidenceReference",
]
