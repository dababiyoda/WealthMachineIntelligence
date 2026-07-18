"""Conservative bootstrap policy for the current WealthMachine actions."""

from __future__ import annotations

from typing import Iterable

from .evidence import EvidenceLedger
from .gateway import ExecutionGateway
from .models import ActionDefinition, AutonomyStage, RiskTier
from .policy_engine import PolicyEngine
from .promotion import PromotionCriteria


DEFAULT_ACTIONS = (
    ActionDefinition(
        "update_venture_status",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Update an internal venture record.",
    ),
    ActionDefinition(
        "trigger_review",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Route an internal review notification.",
    ),
    ActionDefinition(
        "optimize_funnel",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Route an internal optimization task.",
    ),
    ActionDefinition(
        "compliance_review",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Route an internal compliance review.",
    ),
    ActionDefinition(
        "persist_venture_opportunities",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Persist internally generated opportunity hypotheses.",
    ),
    ActionDefinition(
        "persist_venture_metrics",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Persist internal venture metrics with explicit provenance.",
    ),
    ActionDefinition(
        "persist_market_analysis",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Persist a synthetic or observed market-analysis artifact.",
    ),
    ActionDefinition(
        "persist_sentiment",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Persist a sentiment-analysis artifact as internal evidence.",
    ),
    ActionDefinition(
        "persist_predictions",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Persist an uncalibrated model-prediction artifact.",
    ),
    ActionDefinition(
        "persist_forecast",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Persist a forecast artifact without granting execution authority.",
    ),
    ActionDefinition(
        "persist_risk_assessment",
        RiskTier.REVERSIBLE_INTERNAL,
        AutonomyStage.SUPERVISED_CANARY,
        description="Persist a risk-screening artifact and mirrored internal state.",
    ),
    ActionDefinition(
        "send_preapproved_message",
        RiskTier.BOUNDED_EXTERNAL,
        AutonomyStage.BOUNDED,
        description="Send content from an approved template to an allowed recipient class.",
    ),
    ActionDefinition(
        "spend_within_envelope",
        RiskTier.BOUNDED_EXTERNAL,
        AutonomyStage.BOUNDED,
        description="Spend within a charter and capability-specific budget envelope.",
    ),
    ActionDefinition(
        "finance.transfer",
        RiskTier.MATERIAL,
        AutonomyStage.BOUNDED,
        required_human_approvals=2,
        description="Transfer funds after approvals bound to the exact intent.",
    ),
    ActionDefinition(
        "legal.sign_material_agreement",
        RiskTier.MATERIAL,
        AutonomyStage.BOUNDED,
        required_human_approvals=2,
        description="Execute a material or non-standard agreement under dual control.",
    ),
    ActionDefinition(
        "constitutional.change_policy",
        RiskTier.CONSTITUTIONAL,
        AutonomyStage.SCALED_BOUNDED,
        description="Change the charter, control policy, monitoring, or kill conditions.",
    ),
)


PROMOTION_LADDER = {
    AutonomyStage.SHADOW: PromotionCriteria(
        minimum_trials=10,
        minimum_observation_days=0,
        maximum_failure_upper_bound=0.30,
        minimum_rollback_drills=0,
        require_red_team=False,
    ),
    AutonomyStage.SUPERVISED_CANARY: PromotionCriteria(
        minimum_trials=29,
        minimum_observation_days=7,
        maximum_failure_upper_bound=0.10,
        minimum_rollback_drills=1,
        require_red_team=True,
    ),
    AutonomyStage.BOUNDED: PromotionCriteria(
        minimum_trials=99,
        minimum_observation_days=14,
        maximum_failure_upper_bound=0.03,
        minimum_rollback_drills=2,
        require_red_team=True,
    ),
    AutonomyStage.SCALED_BOUNDED: PromotionCriteria(
        minimum_trials=299,
        minimum_observation_days=30,
        maximum_failure_upper_bound=0.01,
        minimum_rollback_drills=3,
        require_red_team=True,
    ),
}


def build_default_control_plane(
    *,
    root_actor_id: str,
    human_authorities: Iterable[str] = (),
    evidence_ledger: EvidenceLedger | None = None,
    policy_version: str = "v1",
) -> tuple[PolicyEngine, ExecutionGateway]:
    engine = PolicyEngine(
        root_authorities={root_actor_id},
        human_authorities=set(human_authorities),
        evidence_ledger=evidence_ledger,
        policy_version=policy_version,
    )
    for definition in DEFAULT_ACTIONS:
        engine.register_action_definition(root_actor_id, definition)
        for target_stage, criteria in PROMOTION_LADDER.items():
            engine.set_promotion_criteria(
                root_actor_id,
                definition.action_type,
                target_stage,
                criteria,
            )
    return engine, ExecutionGateway(engine)


__all__ = [
    "DEFAULT_ACTIONS",
    "PROMOTION_LADDER",
    "build_default_control_plane",
]
