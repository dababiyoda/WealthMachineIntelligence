"""
Decision Engine
===============

The decision engine interprets rule definitions and executes
appropriate actions when those conditions are met.  Rules are defined
in JSON format (see ``automation/sample-rules.json`` from the
original repository) and consist of a nested condition tree and an
action specification.  This module provides a full parser for that
format along with a runtime evaluator.

Example
-------

>>> engine = DecisionEngine.from_json_file('rules.json')
>>> outcomes = engine.evaluate(venture_id, {
...     'market_volatility': 0.9,
...     'risk_profile': 'High'
... })
>>> # outcomes will contain a list of executed actions

The engine is intentionally decoupled from FastAPI and can be used
independently in background tasks or CLIs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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

    def evaluate(self, venture_id: str, venture_type_metrics: Dict[str, Any], connector: KnowledgeGraphConnector) -> Optional[Dict[str, Any]]:
        """Evaluate the rule and execute its action if the condition holds.

        Returns a dict describing the executed action or None if the
        condition is not met.
        """
        if not self.condition.evaluate(venture_type_metrics):
            return None
        logger.debug("Rule triggered", extra={"rule_id": self.rule_id, "venture_id": venture_id})
        return self._execute_action(venture_id, venture_type_metrics, connector)

    def _execute_action(self, venture_id: str, metrics: Dict[str, Any], connector: KnowledgeGraphConnector) -> Dict[str, Any]:
        action_type = self.action.type
        params = self.action.parameters
        outcome: Dict[str, Any] = {"rule_id": self.rule_id, "action_type": action_type}

        if action_type == "update_venture_status":
            new_status = params.get("new_status") or params.get("status")
            connector.update_venture_status(venture_id, new_status)
            # Notify roles if specified
            for role in params.get("notify_roles", []) or []:
                connector.notify_role(role, {
                    "subject": f"Venture {venture_id} status updated to {new_status}",
                    "details": metrics,
                })
            outcome["new_status"] = new_status

        elif action_type == "trigger_review":
            # Assign to a specific role for review
            assignee = params.get("assign_to")
            connector.notify_role(assignee, {
                "subject": f"Venture {venture_id} requires review",
                "required_actions": params.get("required_actions", []),
                "details": metrics,
            })
            outcome["assigned_to"] = assignee

        elif action_type == "optimize_funnel":
            for role in params.get("notify_roles", []) or []:
                connector.notify_role(role, {
                    "subject": f"Optimize funnel for venture {venture_id}",
                    "optimization_areas": params.get("optimization_areas", []),
                    "details": metrics,
                })
            outcome["optimization_areas"] = params.get("optimization_areas", [])

        elif action_type == "compliance_review":
            for role in params.get("notify_roles", []) or []:
                connector.notify_role(role, {
                    "subject": f"Compliance review required for venture {venture_id}",
                    "required_actions": params.get("required_actions", []),
                    "details": metrics,
                })
            outcome["review_roles"] = params.get("notify_roles", [])

        else:
            logger.warning("Unknown action type encountered", extra={"action_type": action_type})
            outcome["error"] = f"Unknown action type {action_type}"

        return outcome


class DecisionEngine:
    """Loads and evaluates a collection of rules against venture metrics."""

    def __init__(self, rules: List[Rule], connector: Optional[KnowledgeGraphConnector] = None) -> None:
        self.rules = rules
        self.connector = connector or KnowledgeGraphConnector()

    @classmethod
    def from_json_file(cls, file_path: Union[str, Path], connector: Optional[KnowledgeGraphConnector] = None) -> 'DecisionEngine':
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
        return cls(rules, connector=connector)

    def evaluate(self, venture_id: str, venture_type: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all applicable rules for a venture and execute actions.

        Returns a list of outcomes describing which rules fired.
        """
        outcomes: List[Dict[str, Any]] = []
        for rule in self.rules:
            if rule.applies_to(venture_type):
                result = rule.evaluate(venture_id, metrics, self.connector)
                if result:
                    outcomes.append(result)
        return outcomes
