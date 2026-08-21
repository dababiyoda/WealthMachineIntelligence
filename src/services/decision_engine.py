"""
Decision Engine
===============

The decision engine interprets rule definitions and proposes appropriate
actions when those conditions are met. Rules are defined
in JSON format (see ``automation/sample-rules.json`` from the
original repository) and consist of a nested condition tree and an
action specification.  This module provides a full parser for that
format along with a runtime evaluator.

Example
-------

>>> engine = DecisionEngine.from_json_file('rules.json')
>>> outcomes = engine.evaluate(venture_id, 'DigitalVenture', {
...     'market_volatility': 0.9,
...     'risk_profile': 'High'
... })
>>> # Without a control gateway, outcomes are proposals and have no side effects.

The engine is intentionally decoupled from FastAPI and can be used
independently in background tasks or CLIs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from ..control.gateway import ExecutionGateway
from ..control.models import ActionIntent, PolicyDisposition, digest
from ..core.knowledge_graph_connector import KnowledgeGraphConnector


logger = logging.getLogger(__name__)


class Operator(str, Enum):
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"

    def evaluate(self, a: Any, b: Any) -> bool:
        """Apply the operator to two values.

        Supports numeric comparison for floats and ints as well as
        string equality.  Missing values return False for strict
        comparisons except for ``not_equals``.
        """
        try:
            if self == Operator.GREATER_THAN:
                return float(a) > float(b)
            if self == Operator.LESS_THAN:
                return float(a) < float(b)
            if self == Operator.EQUALS:
                return a == b
            if self == Operator.NOT_EQUALS:
                return a != b
        except (TypeError, ValueError):
            return False
        return False


@dataclass
class ConditionNode:
    """Represents a condition tree node.

    Each node may contain either a logical operator (AND/OR) with
    children or a leaf comparison on a metric.  The evaluate method
    returns True if the condition holds given a metrics context.
    """
    operator: Optional[str] = None  # 'AND' or 'OR'
    children: Optional[List['ConditionNode']] = None
    metric: Optional[str] = None
    comparator: Optional[Operator] = None
    value: Optional[Any] = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        if self.operator and self.children:
            if self.operator.upper() == "AND":
                return all(child.evaluate(context) for child in self.children)
            if self.operator.upper() == "OR":
                return any(child.evaluate(context) for child in self.children)
        elif self.metric and self.comparator is not None:
            metric_value = context.get(self.metric)
            return self.comparator.evaluate(metric_value, self.value)
        return False

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'ConditionNode':
        """Parse a nested condition dict into a ConditionNode tree."""
        if 'AND' in d:
            return ConditionNode(
                operator='AND',
                children=[ConditionNode.from_dict(x) for x in d['AND']]
            )
        if 'OR' in d:
            return ConditionNode(
                operator='OR',
                children=[ConditionNode.from_dict(x) for x in d['OR']]
            )
        # Leaf condition
        return ConditionNode(
            metric=d.get('metric'),
            comparator=Operator(d.get('operator')),
            value=d.get('value'),
        )


@dataclass
class ActionSpec:
    """Represents an action to execute when a rule is triggered."""
    type: str
    parameters: Dict[str, Any]


@dataclass
class Rule:
    """A decision rule comprised of a condition and an action."""
    rule_id: str
    name: str
    venture_type: str
    condition: ConditionNode
    action: ActionSpec

    def applies_to(self, venture_type: str) -> bool:
        return self.venture_type in (venture_type, "DigitalVenture")

    def evaluate(
        self,
        venture_id: str,
        venture_type_metrics: Dict[str, Any],
        connector: Optional[KnowledgeGraphConnector] = None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate the rule and return a side-effect-free action proposal."""

        if not self.condition.evaluate(venture_type_metrics):
            return None
        logger.debug("Rule triggered", extra={"rule_id": self.rule_id, "venture_id": venture_id})
        return {
            "rule_id": self.rule_id,
            "action_type": self.action.type,
            "execution_status": "proposed",
            "policy_disposition": PolicyDisposition.REVIEW.value,
            "policy_reasons": ["control_gateway_not_configured"],
            "requires_human_approval": True,
        }


class DecisionEngine:
    """Evaluate rules and route every requested side effect through policy."""

    CONTROLLED_ACTIONS = frozenset(
        {
            "update_venture_status",
            "trigger_review",
            "optimize_funnel",
            "compliance_review",
        }
    )

    def __init__(
        self,
        rules: List[Rule],
        connector: Optional[KnowledgeGraphConnector] = None,
        gateway: Optional[ExecutionGateway] = None,
        agent_id: str = "decision-engine",
        context_fingerprint: str = "",
    ) -> None:
        self.rules = rules
        self.connector = connector or KnowledgeGraphConnector()
        self.gateway = gateway
        self.agent_id = agent_id
        self.context_fingerprint = context_fingerprint
        if self.gateway:
            known_actions = self.gateway.policy_engine.action_definitions
            for action_type in self.CONTROLLED_ACTIONS.intersection(known_actions):
                self.gateway.register_executor(action_type, self._execute_intent)

    @classmethod
    def from_json_file(
        cls,
        file_path: Union[str, Path],
        connector: Optional[KnowledgeGraphConnector] = None,
        gateway: Optional[ExecutionGateway] = None,
        agent_id: str = "decision-engine",
        context_fingerprint: str = "",
    ) -> 'DecisionEngine':
        """Construct an engine from a JSON rules file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rules: List[Rule] = []
        for rule_dict in data.get('rules', []):
            condition = ConditionNode.from_dict(rule_dict['condition'])
            action = ActionSpec(
                type=rule_dict['action']['type'],
                parameters=rule_dict['action'].get('parameters', {})
            )
            rules.append(Rule(
                rule_id=rule_dict['id'],
                name=rule_dict.get('name', rule_dict['id']),
                venture_type=rule_dict.get('venture_type', 'DigitalVenture'),
                condition=condition,
                action=action
            ))
        return cls(
            rules,
            connector=connector,
            gateway=gateway,
            agent_id=agent_id,
            context_fingerprint=context_fingerprint,
        )

    def evaluate(self, venture_id: str, venture_type: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate rules and return proposals or control-plane receipts."""

        outcomes: List[Dict[str, Any]] = []
        for rule in self.rules:
            if not rule.applies_to(venture_type):
                continue
            proposal = rule.evaluate(venture_id, metrics)
            if proposal is None:
                continue
            if self.gateway is None:
                outcomes.append(proposal)
                continue

            intent = ActionIntent(
                action_id=self._action_id(rule, venture_id, metrics),
                cell_id=venture_id,
                agent_id=self.agent_id,
                action_type=rule.action.type,
                resource=f"venture:{venture_id}",
                payload={
                    "rule_id": rule.rule_id,
                    "venture_type": venture_type,
                    "parameters": rule.action.parameters,
                    "metrics": metrics,
                },
                context_fingerprint=self.context_fingerprint,
            )
            gateway_result = self.gateway.submit(intent)
            outcome: Dict[str, Any] = {
                "rule_id": rule.rule_id,
                "action_type": rule.action.type,
                "execution_status": (
                    gateway_result.receipt.status
                    if gateway_result.receipt
                    else "not_executed"
                ),
                "policy_disposition": gateway_result.decision.disposition.value,
                "policy_reasons": list(gateway_result.decision.reason_codes),
                "requires_human_approval": (
                    gateway_result.decision.disposition is PolicyDisposition.REVIEW
                ),
            }
            if isinstance(gateway_result.result, Mapping):
                outcome.update(gateway_result.result)
            outcomes.append(outcome)
        return outcomes

    @staticmethod
    def _action_id(rule: Rule, venture_id: str, metrics: Dict[str, Any]) -> str:
        fingerprint = digest(
            {
                "rule_id": rule.rule_id,
                "venture_id": venture_id,
                "action": rule.action,
                "metrics": metrics,
            }
        )
        return f"rule:{rule.rule_id}:{fingerprint[:24]}"

    def _execute_intent(self, intent: ActionIntent) -> Dict[str, Any]:
        """Trusted adapter invoked only by :class:`ExecutionGateway`."""

        if not intent.resource.startswith("venture:"):
            raise ValueError("invalid venture resource")
        venture_id = intent.resource.removeprefix("venture:")
        params = dict(intent.payload.get("parameters", {}))
        metrics = dict(intent.payload.get("metrics", {}))
        action_type = intent.action_type
        outcome: Dict[str, Any] = {"action_type": action_type}

        if action_type == "update_venture_status":
            new_status = params.get("new_status") or params.get("status")
            if not isinstance(new_status, str) or not new_status:
                raise ValueError("new status is required")
            self.connector.update_venture_status(venture_id, new_status)
            for role in params.get("notify_roles", []) or []:
                self.connector.notify_role(
                    role,
                    {
                        "subject": f"Venture {venture_id} status updated to {new_status}",
                        "details": metrics,
                    },
                )
            outcome["new_status"] = new_status

        elif action_type == "trigger_review":
            assignee = params.get("assign_to")
            self.connector.notify_role(
                assignee,
                {
                    "subject": f"Venture {venture_id} requires review",
                    "required_actions": params.get("required_actions", []),
                    "details": metrics,
                },
            )
            outcome["assigned_to"] = assignee

        elif action_type == "optimize_funnel":
            for role in params.get("notify_roles", []) or []:
                self.connector.notify_role(
                    role,
                    {
                        "subject": f"Optimize funnel for venture {venture_id}",
                        "optimization_areas": params.get("optimization_areas", []),
                        "details": metrics,
                    },
                )
            outcome["optimization_areas"] = params.get("optimization_areas", [])

        elif action_type == "compliance_review":
            for role in params.get("notify_roles", []) or []:
                self.connector.notify_role(
                    role,
                    {
                        "subject": f"Compliance review required for venture {venture_id}",
                        "required_actions": params.get("required_actions", []),
                        "details": metrics,
                    },
                )
            outcome["review_roles"] = params.get("notify_roles", [])

        else:
            raise ValueError(f"unsupported controlled action: {action_type}")
        return outcome
