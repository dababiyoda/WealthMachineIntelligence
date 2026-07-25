"""Agent Contracts: the authority an agent has, written down and revocable.

An agent has no standing authority. Whatever it may do is spelled out in an
:class:`AgentContract` — mission, permitted action types, hard limits,
prohibited actions, and escalation triggers — and the Policy Engine treats
everything outside the contract as denied. Contracts are granted by a
human, start at low autonomy, and can be revoked at any time. Autonomy only
increases with documented evidence; it decreases immediately and without
ceremony.

Kept dependency-light on purpose: plain dataclasses, no database. The
registry is the in-memory system of record the policy engine consults; a
persistent backend can replace it later without changing the interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, FrozenSet, List, Optional

# Progressive Autonomy Levels. Every cell/agent starts at 0 or 1 — never
# higher — and promotion requires externally sourced evidence recorded in
# the Evidence Ledger. See docs/PROGRESSIVE_AUTONOMY_LEVELS.md.
AUTONOMY_LEVELS: Dict[int, str] = {
    0: "observe",            # read and analyze only; every action escalates
    1: "propose",            # may draft proposals and assessments for humans
    2: "execute_reversible", # reversible, low-consequence actions within limits
    3: "execute_bounded",    # reversible medium-consequence actions within limits
    4: "conditional",        # reserved; high/irreversible actions still escalate
}
MAX_AUTONOMY_LEVEL = max(AUTONOMY_LEVELS)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentContract:
    """The written scope of one agent's authority.

    ``permitted_actions`` is a whitelist of action types; anything not on
    it is denied by the policy engine (default-deny). ``limits`` are hard
    numeric ceilings (e.g. ``max_spend_usd``, ``max_actions_per_day``).
    ``prohibited_actions`` are denied even if someone later adds them to
    the whitelist — a tripwire against contract editing mistakes.
    """

    agent_id: str
    mission: str
    autonomy_level: int = 0
    permitted_actions: FrozenSet[str] = frozenset()
    limits: Dict[str, float] = field(default_factory=dict)
    prohibited_actions: FrozenSet[str] = frozenset()
    escalation_triggers: List[str] = field(default_factory=list)
    granted_by: str = "operator"
    granted_at: str = field(default_factory=_utcnow)
    revoked: bool = False
    revoked_reason: str = ""

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.mission:
            raise ValueError("mission is required")
        if self.autonomy_level not in AUTONOMY_LEVELS:
            raise ValueError(
                f"autonomy_level must be one of {sorted(AUTONOMY_LEVELS)}"
            )
        self.permitted_actions = frozenset(self.permitted_actions)
        self.prohibited_actions = frozenset(self.prohibited_actions)
        overlap = self.permitted_actions & self.prohibited_actions
        if overlap:
            raise ValueError(
                f"actions cannot be both permitted and prohibited: {sorted(overlap)}"
            )
        for key, value in self.limits.items():
            if float(value) < 0:
                raise ValueError(f"limit {key} must be non-negative")

    def limit(self, key: str) -> Optional[float]:
        value = self.limits.get(key)
        return None if value is None else float(value)


class ContractRegistry:
    """In-memory system of record for agent contracts.

    Promotion demands evidence; demotion and revocation never do. Every
    level change is reported to the ledger callback (wired up by the
    policy engine or the caller) so the history is reconstructable.
    """

    def __init__(self) -> None:
        self._contracts: Dict[str, AgentContract] = {}
        self._level_history: List[Dict[str, object]] = []

    def register(self, contract: AgentContract) -> AgentContract:
        # New authority always starts low: whatever the caller drafted,
        # a fresh contract cannot enter above level 1.
        if contract.agent_id in self._contracts:
            raise ValueError(f"contract already exists for {contract.agent_id}")
        if contract.autonomy_level > 1:
            raise ValueError(
                "new contracts must start at autonomy level 0 or 1; "
                "earn higher levels through set_autonomy_level with evidence"
            )
        self._contracts[contract.agent_id] = contract
        self._record_change(contract.agent_id, None, contract.autonomy_level,
                            reason="contract granted", evidence_refs=[])
        return contract

    def get(self, agent_id: str) -> Optional[AgentContract]:
        return self._contracts.get(agent_id)

    def revoke(self, agent_id: str, reason: str) -> AgentContract:
        contract = self._require(agent_id)
        contract.revoked = True
        contract.revoked_reason = reason or "revoked"
        self._record_change(agent_id, contract.autonomy_level, None,
                            reason=f"revoked: {contract.revoked_reason}",
                            evidence_refs=[])
        return contract

    def set_autonomy_level(
        self,
        agent_id: str,
        new_level: int,
        *,
        reason: str,
        evidence_refs: Optional[List[str]] = None,
        changed_by: str = "operator",
    ) -> AgentContract:
        """Change an agent's autonomy level.

        Increases require at least one evidence reference (pointing into
        the Evidence Ledger) and a reason. Decreases apply immediately and
        need only a reason — regression must never be slower than
        promotion.
        """
        contract = self._require(agent_id)
        if contract.revoked:
            raise ValueError(f"contract for {agent_id} is revoked")
        if new_level not in AUTONOMY_LEVELS:
            raise ValueError(f"autonomy_level must be one of {sorted(AUTONOMY_LEVELS)}")
        if not reason:
            raise ValueError("a reason is required for every autonomy change")
        evidence_refs = list(evidence_refs or [])
        if new_level > contract.autonomy_level and not evidence_refs:
            raise ValueError(
                "autonomy increases require documented evidence references"
            )
        old_level = contract.autonomy_level
        contract.autonomy_level = new_level
        self._record_change(agent_id, old_level, new_level, reason=reason,
                            evidence_refs=evidence_refs, changed_by=changed_by)
        return contract

    @property
    def level_history(self) -> List[Dict[str, object]]:
        return list(self._level_history)

    def _require(self, agent_id: str) -> AgentContract:
        contract = self._contracts.get(agent_id)
        if contract is None:
            raise ValueError(f"no contract registered for {agent_id}")
        return contract

    def _record_change(
        self,
        agent_id: str,
        old_level: Optional[int],
        new_level: Optional[int],
        *,
        reason: str,
        evidence_refs: List[str],
        changed_by: str = "operator",
    ) -> None:
        self._level_history.append({
            "agent_id": agent_id,
            "old_level": old_level,
            "new_level": new_level,
            "reason": reason,
            "evidence_refs": list(evidence_refs),
            "changed_by": changed_by,
            "at": _utcnow(),
        })


__all__ = [
    "AUTONOMY_LEVELS",
    "MAX_AUTONOMY_LEVEL",
    "AgentContract",
    "ContractRegistry",
]
