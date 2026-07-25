"""Policy Evaluation Engine: every consequential action is evaluated here.

The engine answers one question — may this agent take this action right
now? — and gives one of three answers:

* ``allow``    — inside the agent's contract, limits, and autonomy level.
* ``escalate`` — legitimate but above the agent's authority; a human (or
  dual control) must approve before anything happens.
* ``deny``     — outside the contract or on the prohibited list; it does
  not happen and does not get retried into happening.

Doctrine rules are hardcoded, not configuration. Default is deny: an
action type a contract does not explicitly permit is refused. Every
evaluation — including allows — lands in an append-only decision log so
the history of what was attempted is reconstructable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.control.contracts import ContractRegistry

logger = logging.getLogger(__name__)

ALLOWED_VERDICTS = frozenset({"allow", "escalate", "deny"})

ALLOWED_REVERSIBILITY = frozenset({"reversible", "hard_to_reverse", "irreversible"})

ALLOWED_CONSEQUENCE = frozenset({"low", "medium", "high"})

# What an action does to the world. Observing and proposing never touch
# it; executing does, and is what the autonomy ladder actually gates.
ALLOWED_CATEGORIES = frozenset({"observe", "propose", "execute"})

# Actions no contract can ever permit. These are attacks on the control
# layer itself or on the people the system touches — the answer is deny,
# regardless of autonomy level, evidence, or who asks.
GLOBALLY_PROHIBITED_ACTIONS = frozenset({
    "self_authorize",
    "modify_own_contract",
    "raise_own_autonomy",
    "disable_guardrails",
    "bypass_policy_engine",
    "delete_evidence",
    "promise_returns",
    "personalized_financial_advice",
})

# The most consequence an autonomy level may execute without escalation.
# Irreversible/high-consequence actions escalate at every level — level 4
# exists as a ceiling, not an exemption. Levels 0 and 1 execute nothing.
_LEVEL_MAX_CONSEQUENCE = {0: None, 1: None, 2: "low", 3: "medium", 4: "medium"}


@dataclass
class ActionRequest:
    """A single proposed action, described honestly enough to judge it."""

    agent_id: str
    action_type: str
    description: str = ""
    category: str = "execute"         # observe | propose | execute
    consequence: str = "medium"       # low | medium | high
    reversibility: str = "reversible" # reversible | hard_to_reverse | irreversible
    spend_usd: float = 0.0
    venture_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.action_type:
            raise ValueError("action_type is required")
        if self.category not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(ALLOWED_CATEGORIES)}")
        if self.consequence not in ALLOWED_CONSEQUENCE:
            raise ValueError(f"consequence must be one of {sorted(ALLOWED_CONSEQUENCE)}")
        if self.reversibility not in ALLOWED_REVERSIBILITY:
            raise ValueError(
                f"reversibility must be one of {sorted(ALLOWED_REVERSIBILITY)}"
            )
        self.spend_usd = float(self.spend_usd)
        if self.spend_usd < 0:
            raise ValueError("spend_usd must be non-negative")


@dataclass
class PolicyDecision:
    """The engine's verdict on one ActionRequest, with its reasoning."""

    verdict: str
    reasons: List[str]
    request: ActionRequest
    id: str = field(default_factory=lambda: str(uuid4()))
    requires_human_approval: bool = False
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def allowed(self) -> bool:
        return self.verdict == "allow"

    def to_dict(self) -> Dict[str, Any]:
        """Wire/JSON form of the decision for audit surfaces."""
        return {
            "id": self.id,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "requires_human_approval": self.requires_human_approval,
            "evaluated_at": self.evaluated_at,
            "agent_id": self.request.agent_id,
            "action_type": self.request.action_type,
            "category": self.request.category,
            "consequence": self.request.consequence,
            "reversibility": self.request.reversibility,
            "spend_usd": self.request.spend_usd,
            "venture_id": self.request.venture_id,
        }


class PolicyEngine:
    """Evaluates ActionRequests against doctrine rules and agent contracts."""

    def __init__(self, registry: Optional[ContractRegistry] = None) -> None:
        self.registry = registry or ContractRegistry()
        self._decision_log: List[PolicyDecision] = []

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #
    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        verdict, reasons, needs_human = self._judge(request)
        decision = PolicyDecision(
            verdict=verdict,
            reasons=reasons,
            request=request,
            requires_human_approval=needs_human,
        )
        self._decision_log.append(decision)
        logger.info(
            "policy_decision agent=%s action=%s verdict=%s reasons=%s",
            request.agent_id, request.action_type, verdict, reasons,
        )
        return decision

    def _judge(self, request: ActionRequest) -> tuple[str, List[str], bool]:
        # Rule 0: some actions are never on the table, contract or not.
        if request.action_type in GLOBALLY_PROHIBITED_ACTIONS:
            return "deny", [
                f"'{request.action_type}' is globally prohibited; no contract can permit it"
            ], False

        # Rule 1: no contract, no authority.
        contract = self.registry.get(request.agent_id)
        if contract is None:
            return "deny", [
                f"no contract registered for agent '{request.agent_id}'"
            ], False
        if contract.revoked:
            return "deny", [
                f"contract for '{request.agent_id}' is revoked: {contract.revoked_reason}"
            ], False

        # Rule 2: the contract's own prohibited list beats everything else in it.
        if request.action_type in contract.prohibited_actions:
            return "deny", [
                f"'{request.action_type}' is prohibited by the agent's contract"
            ], False

        # Rule 3: default-deny — an action type must be explicitly permitted.
        if request.action_type not in contract.permitted_actions:
            return "deny", [
                f"'{request.action_type}' is not in the contract's permitted actions"
            ], False

        # Rule 4: hard limits. Over-limit spend is not negotiated upward;
        # it goes to a human.
        reasons: List[str] = []
        max_spend = contract.limit("max_spend_usd")
        if request.spend_usd > 0 and max_spend is not None and request.spend_usd > max_spend:
            return "escalate", [
                f"spend {request.spend_usd:.2f} USD exceeds the contract limit "
                f"of {max_spend:.2f} USD"
            ], True
        if request.spend_usd > 0 and max_spend is None:
            return "escalate", [
                "the contract sets no spend limit; any spend requires human approval"
            ], True

        # Rule 5: irreversible or high-consequence actions always escalate,
        # at every autonomy level. Observing and proposing never touch the
        # world, so the gate applies to execution.
        if request.category == "execute" and (
            request.reversibility == "irreversible" or request.consequence == "high"
        ):
            return "escalate", [
                "irreversible or high-consequence actions require human approval "
                f"(consequence={request.consequence}, reversibility={request.reversibility})"
            ], True

        # Rule 6: autonomy-level gating. Level 0 observes; level 1 may also
        # propose; execution starts at level 2 and is consequence-capped.
        if request.category == "propose" and contract.autonomy_level < 1:
            return "escalate", [
                "autonomy level 0 may only observe; proposals require level 1"
            ], True
        if request.category == "execute":
            max_consequence = _LEVEL_MAX_CONSEQUENCE[contract.autonomy_level]
            if max_consequence is None:
                return "escalate", [
                    f"autonomy level {contract.autonomy_level} may only observe/propose; "
                    "execution requires human approval"
                ], True
            order = {"low": 0, "medium": 1, "high": 2}
            if order[request.consequence] > order[max_consequence]:
                return "escalate", [
                    f"consequence '{request.consequence}' exceeds what autonomy level "
                    f"{contract.autonomy_level} may execute ('{max_consequence}')"
                ], True
            if request.reversibility == "hard_to_reverse" and contract.autonomy_level < 3:
                return "escalate", [
                    "hard-to-reverse actions require autonomy level 3 or human approval"
                ], True

        # Escalation triggers named in the contract are honored verbatim.
        for trigger in contract.escalation_triggers:
            if trigger and trigger in request.action_type:
                return "escalate", [
                    f"action matches contract escalation trigger '{trigger}'"
                ], True

        reasons.append(
            f"within contract for '{request.agent_id}' at autonomy level "
            f"{contract.autonomy_level}"
        )
        return "allow", reasons, False

    # ------------------------------------------------------------------ #
    # Decision log (append-only)
    # ------------------------------------------------------------------ #
    @property
    def decision_log(self) -> List[PolicyDecision]:
        return list(self._decision_log)

    def decisions_for(self, agent_id: str) -> List[PolicyDecision]:
        return [d for d in self._decision_log if d.request.agent_id == agent_id]


__all__ = [
    "ALLOWED_VERDICTS",
    "ALLOWED_REVERSIBILITY",
    "ALLOWED_CONSEQUENCE",
    "GLOBALLY_PROHIBITED_ACTIONS",
    "ActionRequest",
    "PolicyDecision",
    "PolicyEngine",
]
