"""Statistical assurance gates for expanding a capability lease."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


def _binomial_cdf(failures: int, trials: int, probability: float) -> float:
    if probability <= 0:
        return 1.0
    if probability >= 1:
        return 1.0 if failures >= trials else 0.0
    logs = []
    for observed in range(failures + 1):
        logs.append(
            math.lgamma(trials + 1)
            - math.lgamma(observed + 1)
            - math.lgamma(trials - observed + 1)
            + observed * math.log(probability)
            + (trials - observed) * math.log1p(-probability)
        )
    largest = max(logs)
    return math.exp(largest) * sum(math.exp(item - largest) for item in logs)


def one_sided_failure_upper_bound(
    failures: int,
    trials: int,
    confidence: float = 0.95,
) -> float:
    """Return the exact one-sided Clopper-Pearson upper failure bound."""

    if trials <= 0:
        raise ValueError("trials must be positive")
    if failures < 0 or failures > trials:
        raise ValueError("failures must be between zero and trials")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    if failures == trials:
        return 1.0

    alpha = 1.0 - confidence
    if failures == 0:
        return 1.0 - alpha ** (1.0 / trials)

    lower = failures / trials
    upper = 1.0
    for _ in range(80):
        midpoint = (lower + upper) / 2.0
        if _binomial_cdf(failures, trials, midpoint) > alpha:
            lower = midpoint
        else:
            upper = midpoint
    return upper


def minimum_zero_failure_trials(
    maximum_failure_rate: float,
    confidence: float = 0.95,
) -> int:
    """Trials needed for a zero-failure upper bound below a target rate."""

    if not 0 < maximum_failure_rate < 1:
        raise ValueError("maximum_failure_rate must be between zero and one")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    return math.ceil(
        math.log(1.0 - confidence) / math.log(1.0 - maximum_failure_rate)
    )


@dataclass(frozen=True)
class PromotionEvidence:
    trials: int
    failures: int
    observation_days: int
    audit_completeness: float
    rollback_drills: int
    policy_violations: int
    critical_incidents: int
    red_team_critical_findings: Optional[int]
    context_fingerprint: str


@dataclass(frozen=True)
class PromotionCriteria:
    minimum_trials: int
    minimum_observation_days: int
    maximum_failure_upper_bound: float
    minimum_audit_completeness: float = 1.0
    minimum_rollback_drills: int = 1
    require_red_team: bool = True
    maximum_policy_violations: int = 0
    maximum_critical_incidents: int = 0
    maximum_red_team_critical_findings: int = 0


@dataclass(frozen=True)
class PromotionEvaluation:
    passed: bool
    reasons: tuple[str, ...]
    failure_upper_bound: float


class PromotionEvaluator:
    """Evaluate control reliability; commercial performance is separate."""

    def evaluate(
        self,
        evidence: PromotionEvidence,
        criteria: PromotionCriteria,
    ) -> PromotionEvaluation:
        reasons: list[str] = []
        if evidence.trials < criteria.minimum_trials:
            reasons.append("insufficient_trials")
        if evidence.observation_days < criteria.minimum_observation_days:
            reasons.append("insufficient_observation_window")
        if evidence.audit_completeness < criteria.minimum_audit_completeness:
            reasons.append("incomplete_audit_evidence")
        if evidence.rollback_drills < criteria.minimum_rollback_drills:
            reasons.append("rollback_not_proven")
        if evidence.policy_violations > criteria.maximum_policy_violations:
            reasons.append("policy_violations_exceeded")
        if evidence.critical_incidents > criteria.maximum_critical_incidents:
            reasons.append("critical_incidents_exceeded")
        if criteria.require_red_team and evidence.red_team_critical_findings is None:
            reasons.append("red_team_missing")
        elif (
            evidence.red_team_critical_findings is not None
            and evidence.red_team_critical_findings
            > criteria.maximum_red_team_critical_findings
        ):
            reasons.append("red_team_critical_findings")

        failure_upper_bound = one_sided_failure_upper_bound(
            evidence.failures,
            evidence.trials,
        )
        if failure_upper_bound > criteria.maximum_failure_upper_bound:
            reasons.append("failure_bound_exceeded")
        return PromotionEvaluation(
            passed=not reasons,
            reasons=tuple(reasons),
            failure_upper_bound=failure_upper_bound,
        )


__all__ = [
    "PromotionCriteria",
    "PromotionEvaluation",
    "PromotionEvaluator",
    "PromotionEvidence",
    "minimum_zero_failure_trials",
    "one_sided_failure_upper_bound",
]
