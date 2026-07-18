"""Policy-mediated adapters for knowledge-graph and mirrored database writes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Iterable

from ..core.knowledge_graph_connector import KnowledgeGraphConnector
from .gateway import ExecutionGateway
from .models import ActionIntent, PolicyDisposition, digest


GRAPH_MUTATION_ACTIONS = frozenset(
    {
        "persist_venture_opportunities",
        "persist_venture_metrics",
        "persist_market_analysis",
        "persist_sentiment",
        "persist_predictions",
        "persist_forecast",
        "persist_risk_assessment",
    }
)


class KnowledgeGraphActionAdapter:
    """Trusted adapter installed during application bootstrap."""

    def __init__(
        self,
        gateway: ExecutionGateway,
        connector: KnowledgeGraphConnector,
    ) -> None:
        self.gateway = gateway
        self.connector = connector
        registered_actions = gateway.policy_engine.action_definitions
        for action_type in GRAPH_MUTATION_ACTIONS.intersection(registered_actions):
            gateway.register_executor(action_type, self.execute)

    def execute(self, intent: ActionIntent) -> dict[str, str]:
        """Validate payload shape and dispatch one gateway-authorized write."""

        expected_resource = f"venture:{intent.cell_id}"
        if intent.resource != expected_resource:
            raise ValueError("graph mutations require the exact cell venture resource")

        venture_id = intent.cell_id
        payload = dict(intent.payload)
        action_type = intent.action_type

        if action_type == "persist_venture_opportunities":
            opportunities = payload.get("opportunities")
            if not isinstance(opportunities, list):
                raise ValueError("opportunities must be a list")
            self.connector.update_opportunities(venture_id, opportunities)
        elif action_type == "persist_venture_metrics":
            self.connector.update_venture_metrics(
                venture_id,
                self._mapping(payload, "metrics"),
            )
        elif action_type == "persist_market_analysis":
            self.connector.store_market_analysis(
                venture_id,
                self._mapping(payload, "analysis"),
            )
        elif action_type == "persist_sentiment":
            self.connector.store_sentiment(
                venture_id,
                self._mapping(payload, "sentiment"),
            )
        elif action_type == "persist_predictions":
            self.connector.store_predictions(
                venture_id,
                self._mapping(payload, "predictions"),
            )
        elif action_type == "persist_forecast":
            self.connector.store_forecast(
                venture_id,
                self._mapping(payload, "forecast"),
            )
        elif action_type == "persist_risk_assessment":
            assessment = self._mapping(payload, "assessment")
            if not assessment.get("agent_id"):
                raise ValueError(
                    "risk persistence requires a root-provisioned persistent agent_id"
                )
            self.connector.store_risk_assessment(
                venture_id,
                assessment,
            )
        else:
            raise ValueError(f"unsupported graph mutation action: {action_type}")

        return {
            "id": f"{action_type}:{venture_id}",
            "venture_id": venture_id,
        }

    @staticmethod
    def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
        value = payload.get(key)
        if not isinstance(value, Mapping):
            raise ValueError(f"{key} must be an object")
        return dict(value)


class GraphIntentClient:
    """Create graph-write intents; remain proposal-only without a gateway."""

    def __init__(
        self,
        gateway: ExecutionGateway | None,
        *,
        agent_id: str,
        context_fingerprint: str,
        data_classes: Iterable[str] = ("internal",),
    ) -> None:
        self.gateway = gateway
        self.agent_id = agent_id
        self.context_fingerprint = context_fingerprint
        self.data_classes = frozenset(data_classes)

    def submit(
        self,
        action_type: str,
        venture_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if action_type not in GRAPH_MUTATION_ACTIONS:
            raise ValueError("unsupported graph mutation action")

        action_id = self._action_id(action_type, venture_id, payload)
        if self.gateway is None:
            return {
                "action_id": action_id,
                "action_type": action_type,
                "execution_status": "proposed",
                "policy_disposition": PolicyDisposition.REVIEW.value,
                "policy_reasons": ["control_gateway_not_configured"],
                "requires_human_approval": True,
            }

        intent = ActionIntent(
            action_id=action_id,
            cell_id=venture_id,
            agent_id=self.agent_id,
            action_type=action_type,
            resource=f"venture:{venture_id}",
            payload=dict(payload),
            data_classes=self.data_classes,
            context_fingerprint=self.context_fingerprint,
        )
        result = self.gateway.submit(intent)
        outcome: dict[str, Any] = {
            "action_id": action_id,
            "action_type": action_type,
            "execution_status": (
                result.receipt.status if result.receipt else "not_executed"
            ),
            "policy_disposition": result.decision.disposition.value,
            "policy_reasons": list(result.decision.reason_codes),
            "requires_human_approval": (
                result.decision.disposition is PolicyDisposition.REVIEW
            ),
        }
        if isinstance(result.result, Mapping):
            outcome.update(result.result)
        return outcome

    def _action_id(
        self,
        action_type: str,
        venture_id: str,
        payload: Mapping[str, Any],
    ) -> str:
        fingerprint = digest(
            {
                "agent_id": self.agent_id,
                "action_type": action_type,
                "venture_id": venture_id,
                "payload": payload,
                "context_fingerprint": self.context_fingerprint,
            }
        )
        return f"graph:{action_type}:{fingerprint[:24]}"


__all__ = [
    "GRAPH_MUTATION_ACTIONS",
    "GraphIntentClient",
    "KnowledgeGraphActionAdapter",
]
