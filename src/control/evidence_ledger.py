"""Evidence Ledger and Assumption Register.

The ledger is the memory the system is not allowed to lose: what we
assumed, what we tested, what the world said back, and what we decided.
It is append-only — records are never edited or deleted. An assumption's
status changes by appending a status event, so the full history of how a
belief moved from untested to supported (or refuted) survives.

Kept as plain dicts in memory: the point at this phase is the discipline
and the interfaces, not the storage engine. A database can take over
persistence later without changing a caller.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

ASSUMPTION_STATUSES = frozenset({"untested", "testing", "supported", "refuted"})

# Evidence sourced outside the system (customer replies, payments,
# regulator text) is what earns autonomy; internal model output does not.
EVIDENCE_KINDS = frozenset({"external", "internal"})


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceLedger:
    """Append-only register of assumptions, evidence, experiments, decisions."""

    def __init__(self) -> None:
        self._assumptions: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Assumption Register
    # ------------------------------------------------------------------ #
    def add_assumption(
        self,
        statement: str,
        *,
        venture_id: str = "",
        criticality: str = "medium",
        source: str = "",
    ) -> Dict[str, Any]:
        if not statement:
            raise ValueError("an assumption needs a statement")
        if criticality not in ("low", "medium", "high"):
            raise ValueError("criticality must be low, medium, or high")
        assumption = {
            "id": str(uuid4()),
            "statement": statement,
            "venture_id": venture_id,
            "criticality": criticality,
            "source": source,
            "status": "untested",
            "created_at": _utcnow(),
        }
        self._assumptions[assumption["id"]] = assumption
        self._append("assumption_added", assumption)
        return dict(assumption)

    def set_assumption_status(
        self, assumption_id: str, status: str, *, evidence_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Move an assumption between statuses by appending a status event.

        Marking an assumption ``supported`` or ``refuted`` requires at
        least one evidence reference — beliefs do not change for free.
        """
        assumption = self._assumptions.get(assumption_id)
        if assumption is None:
            raise ValueError(f"unknown assumption {assumption_id}")
        if status not in ASSUMPTION_STATUSES:
            raise ValueError(f"status must be one of {sorted(ASSUMPTION_STATUSES)}")
        evidence_ids = list(evidence_ids or [])
        if status in ("supported", "refuted") and not evidence_ids:
            raise ValueError(f"marking an assumption {status} requires evidence ids")
        old_status = assumption["status"]
        assumption["status"] = status
        self._append("assumption_status_changed", {
            "assumption_id": assumption_id,
            "old_status": old_status,
            "new_status": status,
            "evidence_ids": evidence_ids,
        })
        return dict(assumption)

    def get_assumption(self, assumption_id: str) -> Optional[Dict[str, Any]]:
        found = self._assumptions.get(assumption_id)
        return dict(found) if found else None

    # ------------------------------------------------------------------ #
    # Evidence, experiments, decisions
    # ------------------------------------------------------------------ #
    def record_evidence(
        self,
        summary: str,
        *,
        kind: str = "external",
        venture_id: str = "",
        assumption_id: str = "",
        source: str = "",
        strength: str = "weak",
    ) -> Dict[str, Any]:
        if not summary:
            raise ValueError("evidence needs a summary")
        if kind not in EVIDENCE_KINDS:
            raise ValueError(f"kind must be one of {sorted(EVIDENCE_KINDS)}")
        if strength not in ("weak", "moderate", "strong"):
            raise ValueError("strength must be weak, moderate, or strong")
        if assumption_id and assumption_id not in self._assumptions:
            raise ValueError(f"unknown assumption {assumption_id}")
        record = {
            "id": str(uuid4()),
            "summary": summary,
            "kind": kind,
            "venture_id": venture_id,
            "assumption_id": assumption_id,
            "source": source,
            "strength": strength,
            "recorded_at": _utcnow(),
        }
        self._append("evidence_recorded", record)
        return dict(record)

    def record_experiment(
        self,
        hypothesis: str,
        method: str,
        *,
        venture_id: str = "",
        assumption_id: str = "",
        result: str = "",
        status: str = "planned",
    ) -> Dict[str, Any]:
        if not hypothesis or not method:
            raise ValueError("an experiment needs a hypothesis and a method")
        if status not in ("planned", "running", "concluded"):
            raise ValueError("status must be planned, running, or concluded")
        record = {
            "id": str(uuid4()),
            "hypothesis": hypothesis,
            "method": method,
            "venture_id": venture_id,
            "assumption_id": assumption_id,
            "result": result,
            "status": status,
            "recorded_at": _utcnow(),
        }
        self._append("experiment_recorded", record)
        return dict(record)

    def record_decision(
        self,
        decision: str,
        *,
        venture_id: str = "",
        actor: str = "system",
        reasons: Optional[List[str]] = None,
        evidence_ids: Optional[List[str]] = None,
        requires_human_approval: bool = True,
    ) -> Dict[str, Any]:
        if not decision:
            raise ValueError("a decision needs a statement")
        record = {
            "id": str(uuid4()),
            "decision": decision,
            "venture_id": venture_id,
            "actor": actor,
            "reasons": list(reasons or []),
            "evidence_ids": list(evidence_ids or []),
            "requires_human_approval": bool(requires_human_approval),
            "recorded_at": _utcnow(),
        }
        self._append("decision_recorded", record)
        return dict(record)

    # ------------------------------------------------------------------ #
    # Reading the ledger
    # ------------------------------------------------------------------ #
    @property
    def events(self) -> List[Dict[str, Any]]:
        """The full append-only event stream (copies, oldest first)."""
        return [dict(event) for event in self._events]

    def events_for(self, venture_id: str) -> List[Dict[str, Any]]:
        """Every event whose payload names this venture — enough to
        reconstruct the venture's evidentiary history in order."""
        matched = []
        for event in self._events:
            payload = event["payload"]
            if payload.get("venture_id") == venture_id:
                matched.append(dict(event))
                continue
            assumption_id = payload.get("assumption_id")
            if assumption_id:
                assumption = self._assumptions.get(assumption_id)
                if assumption and assumption["venture_id"] == venture_id:
                    matched.append(dict(event))
        return matched

    def assumptions_for(self, venture_id: str) -> List[Dict[str, Any]]:
        return [
            dict(a) for a in self._assumptions.values()
            if a["venture_id"] == venture_id
        ]

    def _append(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events.append({
            "sequence": len(self._events),
            "event_type": event_type,
            "payload": dict(payload),
            "at": _utcnow(),
        })


__all__ = [
    "ASSUMPTION_STATUSES",
    "EVIDENCE_KINDS",
    "EvidenceLedger",
]
