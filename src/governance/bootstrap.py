"""Explicit development-only preview bootstrap.

Production never receives demo authority implicitly.  Operators must opt in to
bootstrap and still receive only R0/R1 analysis and sandbox capability.
"""

from __future__ import annotations

from datetime import timedelta

from typing import Any

from sqlalchemy.orm import Session

from .models import (
    AgentContractRecord,
    BudgetAccountRecord,
    CapabilityGrantRecord,
    GovernanceIdentity,
)
from .service import GovernanceService, utcnow


ALL_HUMAN_AUTHORITIES = [
    "venture_sponsor",
    "designated_human",
    "legal_authority",
    "financial_authority",
    "security_authority",
    "privacy_authority",
    "human_resources_authority",
    "system_governor",
]


def bootstrap_preview(
    session: Session, users: dict[str, dict[str, Any]] | None = None
) -> None:
    """Create bounded local identities and R0/R1 grants idempotently."""

    service = GovernanceService(session)
    expires_at = utcnow() + timedelta(days=30)
    users = users or {}
    identities = []
    for user in users.values():
        is_admin = user.get("role") == "admin"
        identities.append(
            {
                "identity_id": user["user_id"],
                "identity_type": "human",
                "display_name": user["username"],
                "venture_id": "preview",
                "role": "system_governor" if is_admin else "independent_reviewer",
                "attributes": {
                    "authorities": ALL_HUMAN_AUTHORITIES if is_admin else [],
                    "source": "explicit_preview_bootstrap",
                },
                "expires_at": expires_at,
            }
        )
    for payload in identities:
        if not session.get(GovernanceIdentity, payload["identity_id"]):
            service.register_identity(payload, actor_id="bootstrap")

    owner_id = next(
        (user["user_id"] for user in users.values() if user.get("role") == "admin"),
        "bootstrap",
    )
    for identity in identities:
        identity_id = identity["identity_id"]
        contract_id = f"preview-contract-{identity_id}"
        if not session.get(AgentContractRecord, contract_id):
            service.register_contract(
                {
                    "contract_id": contract_id,
                    "subject_id": identity_id,
                    "venture_id": "preview",
                    "mission": "Operate bounded, evidence-linked analysis and sandbox workflows.",
                    "allowed_actions": ["research", "draft", "simulation"],
                    "prohibited_actions": [
                        "spend",
                        "publish",
                        "deploy",
                        "contract",
                        "transfer_funds",
                    ],
                    "allowed_data_classes": ["public", "internal"],
                    "owner_id": owner_id,
                    "expires_at": expires_at,
                },
                actor_id="bootstrap",
            )
        for action_type in ("research", "draft", "simulation"):
            grant_id = f"preview-grant-{identity_id}-{action_type}"
            if not session.get(CapabilityGrantRecord, grant_id):
                service.grant_capability(
                    {
                        "grant_id": grant_id,
                        "subject_id": identity_id,
                        "venture_id": "preview",
                        "action_type": action_type,
                        "environments": ["analysis", "sandbox"],
                        "max_risk_class": "R1",
                        "money_limit_minor": 0,
                        "granted_by": "bootstrap",
                        "expires_at": expires_at,
                    },
                    actor_id="bootstrap",
                )

    if not session.get(BudgetAccountRecord, "preview-budget-usd"):
        service.set_budget(
            {
                "budget_id": "preview-budget-usd",
                "venture_id": "preview",
                "currency": "USD",
                "limit_minor": 0,
                "owner_id": owner_id,
            },
            actor_id="bootstrap",
        )


__all__ = ["ALL_HUMAN_AUTHORITIES", "bootstrap_preview"]
