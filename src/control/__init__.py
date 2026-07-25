"""Constitutional Control Layer.

Every consequential action in the system routes through this package:

* :mod:`contracts` — Agent Contracts: explicit mission, permissions,
  limits, prohibited actions, and escalation rules per agent. No contract,
  no authority.
* :mod:`policy_engine` — the Policy Evaluation Engine. Default-deny
  evaluation of :class:`ActionRequest`s against doctrine rules and the
  requesting agent's contract, with an append-only decision log.
* :mod:`evidence_ledger` — the Evidence Ledger and Assumption Register.
  Append-only record of assumptions, experiments, evidence, decisions,
  and autonomy-level changes.

The doctrine in one line: the machine prepares, the human authorizes, the
world responds, the system learns. Nothing in this package makes an outcome
certain — it makes failure visible, bounded, and reversible.
"""

from src.control.contracts import (
    AgentContract,
    ContractRegistry,
    AUTONOMY_LEVELS,
    MAX_AUTONOMY_LEVEL,
)
from src.control.evidence_ledger import EvidenceLedger
from src.control.policy_engine import (
    ActionRequest,
    PolicyDecision,
    PolicyEngine,
    GLOBALLY_PROHIBITED_ACTIONS,
)

__all__ = [
    "AgentContract",
    "ContractRegistry",
    "AUTONOMY_LEVELS",
    "MAX_AUTONOMY_LEVEL",
    "EvidenceLedger",
    "ActionRequest",
    "PolicyDecision",
    "PolicyEngine",
    "GLOBALLY_PROHIBITED_ACTIONS",
]
