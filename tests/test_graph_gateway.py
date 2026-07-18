"""Bypass tests for policy-mediated knowledge-graph persistence."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest

from src.control import (
    ActionIntent,
    AutonomyStage,
    CapabilityGrant,
    PromotionEvidence,
    VentureCellCharter,
    build_default_control_plane,
)
from src.control.execution_context import UnmediatedSideEffectError
from src.control.graph_adapter import GraphIntentClient, KnowledgeGraphActionAdapter
from src.control.models import utc_now
from src.core.knowledge_graph import knowledge_graph
import src.core.knowledge_graph_connector as connector_module
from src.core.knowledge_graph_connector import KnowledgeGraphConnector
from src.services.risk_management import RiskManager


ROOT = "graph-root"
CONTEXT = "graph-model-v1:prompt-v1:tools-v1"


class CountingConnector(KnowledgeGraphConnector):
    def __init__(self) -> None:
        self.metric_writes = 0

    def update_venture_metrics(self, venture_id, metrics) -> None:
        self.metric_writes += 1
        super().update_venture_metrics(venture_id, metrics)


def _plane(cell_id: str):
    policy, gateway = build_default_control_plane(root_actor_id=ROOT)
    policy.create_cell(
        ROOT,
        VentureCellCharter(
            cell_id=cell_id,
            mission="Exercise one internal persistence capability.",
            owner_id=ROOT,
            allowed_data_classes=frozenset({"internal"}),
        ),
    )
    return policy, gateway


def _grant(policy, cell_id: str, action_type: str, agent_id: str) -> None:
    grant = policy.issue_grant(
        ROOT,
        CapabilityGrant(
            grant_id=f"grant:{cell_id}:{action_type}:{agent_id}",
            cell_id=cell_id,
            agent_id=agent_id,
            action_type=action_type,
            stage=AutonomyStage.SHADOW,
            resource_prefixes=(f"venture:{cell_id}",),
            expires_at=utc_now() + timedelta(hours=1),
            context_fingerprint=CONTEXT,
            allowed_data_classes=frozenset({"internal"}),
        ),
    )
    promotion = policy.promote_grant(
        ROOT,
        grant.grant_id,
        PromotionEvidence(
            trials=29,
            failures=0,
            observation_days=7,
            audit_completeness=1.0,
            rollback_drills=1,
            policy_violations=0,
            critical_incidents=0,
            red_team_critical_findings=0,
            context_fingerprint=CONTEXT,
        ),
        independent_review_id=f"test-review:{grant.grant_id}",
    )
    assert promotion.passed


def test_direct_connector_mutation_fails_before_state_change() -> None:
    venture_id = "graph-direct-bypass"
    connector = KnowledgeGraphConnector()

    with pytest.raises(UnmediatedSideEffectError):
        connector.update_venture_status(venture_id, "Bypassed")

    assert knowledge_graph.get_node(venture_id) is None


def test_authorized_graph_write_is_idempotent_and_context_is_revoked() -> None:
    cell_id = "graph-authorized"
    agent_id = "metrics-writer"
    policy, gateway = _plane(cell_id)
    _grant(policy, cell_id, "persist_venture_metrics", agent_id)
    connector = CountingConnector()
    KnowledgeGraphActionAdapter(gateway, connector)
    client = GraphIntentClient(
        gateway,
        agent_id=agent_id,
        context_fingerprint=CONTEXT,
    )
    payload = {
        "metrics": {"retained_usage": 12},
        "provenance": {"source_type": "external_system"},
    }

    first = client.submit("persist_venture_metrics", cell_id, payload)
    second = client.submit("persist_venture_metrics", cell_id, payload)

    assert first["execution_status"] == "executed"
    assert second["execution_status"] == "executed"
    assert connector.metric_writes == 1
    assert knowledge_graph.get_node(cell_id).properties["retained_usage"] == 12
    with pytest.raises(UnmediatedSideEffectError):
        connector.update_venture_metrics(cell_id, {"retained_usage": 99})


def test_allowed_metrics_intent_cannot_be_reused_for_status_mutation() -> None:
    cell_id = "graph-confused-deputy"
    agent_id = "metrics-writer"
    policy, gateway = _plane(cell_id)
    _grant(policy, cell_id, "persist_venture_metrics", agent_id)
    connector = KnowledgeGraphConnector()
    KnowledgeGraphActionAdapter(gateway, connector)
    gateway.register_executor(
        "persist_venture_metrics",
        lambda intent: connector.update_venture_status(cell_id, "Bypassed"),
    )
    client = GraphIntentClient(
        gateway,
        agent_id=agent_id,
        context_fingerprint=CONTEXT,
    )

    result = client.submit(
        "persist_venture_metrics",
        cell_id,
        {"metrics": {"x": 1}},
    )

    assert result["policy_disposition"] == "allow"
    assert result["execution_status"] == "failed"
    node = knowledge_graph.get_node(cell_id)
    assert node is None or node.properties.get("status") != "Bypassed"


def test_cross_cell_resource_is_denied_before_adapter_execution() -> None:
    cell_id = "graph-cell-a"
    other_cell_id = "graph-cell-b"
    agent_id = "metrics-writer"
    policy, gateway = _plane(cell_id)
    _grant(policy, cell_id, "persist_venture_metrics", agent_id)
    connector = CountingConnector()
    KnowledgeGraphActionAdapter(gateway, connector)
    intent = ActionIntent(
        action_id="cross-cell-graph-write",
        cell_id=cell_id,
        agent_id=agent_id,
        action_type="persist_venture_metrics",
        resource=f"venture:{other_cell_id}",
        payload={"metrics": {"x": 1}},
        data_classes=frozenset({"internal"}),
        context_fingerprint=CONTEXT,
    )

    result = gateway.submit(intent)

    assert result.decision.disposition.value == "deny"
    assert connector.metric_writes == 0
    assert knowledge_graph.get_node(other_cell_id) is None


def test_graph_client_and_risk_manager_are_proposal_only_without_gateway() -> None:
    cell_id = "graph-proposal-only"
    client = GraphIntentClient(
        None,
        agent_id="proposal-writer",
        context_fingerprint=CONTEXT,
    )

    proposal = client.submit(
        "persist_venture_metrics",
        cell_id,
        {"metrics": {"x": 1}},
    )
    risk = asyncio.run(
        RiskManager(context_fingerprint=CONTEXT).assess(
            cell_id,
            {
                "opportunity_score": 0.5,
                "execution_confidence": 0.5,
                "expected_roi": 0.2,
                "risk_buffer": 0.1,
            },
        )
    )

    assert proposal["execution_status"] == "proposed"
    assert risk["persistence"]["execution_status"] == "proposed"
    assert knowledge_graph.get_node(cell_id) is None


def test_risk_persistence_cannot_mint_its_own_agent_identity() -> None:
    cell_id = "graph-risk-no-identity"
    agent_id = "risk-assessment-service"
    policy, gateway = _plane(cell_id)
    _grant(policy, cell_id, "persist_risk_assessment", agent_id)
    KnowledgeGraphActionAdapter(gateway, KnowledgeGraphConnector())
    client = GraphIntentClient(
        gateway,
        agent_id=agent_id,
        context_fingerprint=CONTEXT,
    )

    result = client.submit(
        "persist_risk_assessment",
        cell_id,
        {
            "assessment": {
                "agent_id": None,
                "risk_score": 0.2,
                "failure_probability": 0.004,
            }
        },
    )

    assert result["policy_disposition"] == "allow"
    assert result["execution_status"] == "failed"
    assert knowledge_graph.get_node(cell_id) is None


def test_market_analysis_without_timestamp_persists_non_null_time(
    monkeypatch,
) -> None:
    cell_id = "graph-market-default-timestamp"
    agent_id = "market-writer"
    captured: list[object] = []

    class FakeMarketAnalysis:
        def __init__(self, **values):
            for key, value in values.items():
                setattr(self, key, value)

    class FakeSession:
        def add(self, value) -> None:
            captured.append(value)

    class FakeDatabase:
        @contextmanager
        def get_session(self):
            yield FakeSession()

    monkeypatch.setattr(connector_module, "db", FakeDatabase())
    monkeypatch.setattr(connector_module, "MarketAnalysis", FakeMarketAnalysis)

    policy, gateway = _plane(cell_id)
    _grant(policy, cell_id, "persist_market_analysis", agent_id)
    KnowledgeGraphActionAdapter(gateway, KnowledgeGraphConnector())
    client = GraphIntentClient(
        gateway,
        agent_id=agent_id,
        context_fingerprint=CONTEXT,
    )

    result = client.submit(
        "persist_market_analysis",
        cell_id,
        {
            "analysis": {
                "market_size": 1_000_000,
                "competition_level": "medium",
                "opportunity_score": 0.6,
            }
        },
    )

    assert result["execution_status"] == "executed"
    assert len(captured) == 1
    analyzed_at = captured[0].analyzed_at
    assert isinstance(analyzed_at, datetime)
    assert analyzed_at.tzinfo is not None
