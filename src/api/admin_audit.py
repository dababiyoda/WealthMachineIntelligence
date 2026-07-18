"""Tamper-evident audit trail for authenticated human administration."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..control.evidence import EvidenceLedger


_ledger_path = os.getenv("ADMIN_AUDIT_LEDGER_PATH")
admin_audit_ledger = EvidenceLedger(Path(_ledger_path) if _ledger_path else None)


def record_admin_intent(
    current_user: Mapping[str, Any],
    *,
    action_type: str,
    resource: str,
    changed_fields: Iterable[str] = (),
) -> str:
    """Record intent before an administrative database transaction begins."""

    action_id = f"admin:{uuid.uuid4()}"
    admin_audit_ledger.append(
        "admin_action_intent",
        str(current_user.get("user_id", "unknown-human")),
        {
            "action_type": action_type,
            "resource": resource,
            "changed_fields": sorted(set(changed_fields)),
            "authenticated_role": current_user.get("role"),
        },
        action_id=action_id,
    )
    return action_id


def record_admin_outcome(
    current_user: Mapping[str, Any],
    *,
    action_id: str,
    action_type: str,
    resource: str,
    status: str,
    error_type: str | None = None,
) -> None:
    """Record the result without storing raw request or sensitive content."""

    admin_audit_ledger.append(
        "admin_action_outcome",
        str(current_user.get("user_id", "unknown-human")),
        {
            "action_type": action_type,
            "resource": resource,
            "status": status,
            "error_type": error_type,
        },
        action_id=action_id,
    )


__all__ = [
    "admin_audit_ledger",
    "record_admin_intent",
    "record_admin_outcome",
]
