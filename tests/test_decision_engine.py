"""
Unit tests for the decision engine.

These tests exercise condition parsing, evaluation logic and action
execution without relying on a database.  A minimal ruleset is
constructed inline to verify the expected behaviour.
"""

from src.services.decision_engine import DecisionEngine, ConditionNode, Operator, Rule, ActionSpec
from src.core.knowledge_graph_connector import KnowledgeGraphConnector
from src.core.knowledge_graph import knowledge_graph



def test_operator_evaluation() -> None:
    op = Operator.GREATER_THAN
    assert op.evaluate(0.7, 0.5) is True
    assert op.evaluate(0.3, 0.5) is False
    op = Operator.LESS_THAN
    assert op.evaluate(3, 5) is True
    assert op.evaluate(5, 5) is False
    op = Operator.EQUALS
    assert op.evaluate('High', 'High') is True
    assert op.evaluate('Low', 'High') is False
    op = Operator.NOT_EQUALS
    assert op.evaluate('Low', 'High') is True


def test_condition_node_leaf() -> None:
    c = ConditionNode(metric='x', comparator=Operator.GREATER_THAN, value=10)
    assert c.evaluate({'x': 11}) is True
    assert c.evaluate({'x': 10}) is False
    assert c.evaluate({'x': 9}) is False


def test_condition_node_nested_and_or() -> None:
    # (a > 5 AND b < 3) OR c == 'Yes'
    condition = ConditionNode.from_dict({
        'OR': [
            {
                'AND': [
                    {'metric': 'a', 'operator': 'greater_than', 'value': 5},
                    {'metric': 'b', 'operator': 'less_than', 'value': 3}
                ]
            },
            {
                'metric': 'c', 'operator': 'equals', 'value': 'Yes'
            }
        ]
    })
    assert condition.evaluate({'a': 6, 'b': 2, 'c': 'No'}) is True
    assert condition.evaluate({'a': 6, 'b': 4, 'c': 'Yes'}) is True
    assert condition.evaluate({'a': 4, 'b': 2, 'c': 'No'}) is False


def test_decision_engine_rule_trigger() -> None:
    # Define a simple rule: if metric x > 0.5 -> update status to "Triggered"
    cond = ConditionNode.from_dict({'metric': 'x', 'operator': 'greater_than', 'value': 0.5})
    action = ActionSpec(type='update_venture_status', parameters={'new_status': 'Triggered'})
    rule = Rule(rule_id='r1', name='Test Rule', venture_type='DigitalVenture', condition=cond, action=action)
    connector = KnowledgeGraphConnector()
    engine = DecisionEngine([rule], connector=connector)

    # Prepare metrics that should trigger
    metrics = {'x': 0.6}
    outcomes = engine.evaluate('venture-1', 'DigitalVenture', metrics)
    assert outcomes and outcomes[0]['new_status'] == 'Triggered'
    # Validate that the knowledge graph node now has the updated status
    node = knowledge_graph.get_node('venture-1')
    assert node is not None
    assert node.properties['status'] == 'Triggered'

    # Metrics that do not trigger
    metrics2 = {'x': 0.3}
    outcomes2 = engine.evaluate('venture-2', 'DigitalVenture', metrics2)
    assert outcomes2 == []
    # Node status should not be set
    node2 = knowledge_graph.get_node('venture-2')
    assert node2 is None or node2.properties.get('status') != 'Triggered'
