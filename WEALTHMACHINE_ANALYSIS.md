# WealthMachine Current-State Analysis

## Executive conclusion

WealthMachine is a venture-evaluation and orchestration prototype with useful
domain models, rule evaluation, APIs, tests, and an emerging constitutional
control plane. It is **not evidence for an ultra-low business failure rate**, a
production-ready autonomous venture studio, or a calibrated investment system.

The strongest route is to use the current system for bounded research,
assessment, and shadow-mode workflow validation while progressively making the
execution boundary unavoidable. See:

- `docs/AUTONOMY_ARCHITECTURE_DECISION.md`
- `docs/CONSTITUTIONAL_CONTROL_LAYER.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `docs/SIDE_EFFECT_INVENTORY.md`

## Verified repository capabilities

- specialized agent and venture-domain structures;
- opportunity intake and `VentureAssessment` wire protocol;
- deterministic orchestration and heuristic risk scoring;
- in-memory knowledge graph and SQLAlchemy persistence paths;
- rule parsing and proposal generation;
- a tested policy engine, Venture Cell charter, scoped capability grants,
  execution gateway, Evidence Ledger, Assumption Register, promotion/regression,
  and dual-control primitives; and
- Docker, API, and CI foundations.

## Material limitations

- Several “AI” services use randomized or heuristic outputs rather than trained,
  validated, calibrated models.
- Values stored as `failure_probability` are model-derived heuristics; the
  repository contains no validation demonstrating that they predict real
  venture failure probabilities.
- Several internal database and knowledge-graph writes still bypass the control
  gateway.
- Control identities and state are not yet production-grade or transactional.
- Direct credential and network-egress prevention is not implemented here.
- Commercial viability, legal compliance, security, and model performance have
  not been independently established by this codebase.

## Evidence policy

Internal scores, simulations, draft recommendations, and survey enthusiasm do
not unlock capital or authority. Strong evidence includes paid behavior,
retained usage, contribution economics, representative execution trials,
complete audit records, rollback drills, incidents, and independent red-team
results.

Business evidence controls whether a venture continues. Separate control
assurance determines whether a specific capability may advance by one stage.

## Immediate priorities

1. Complete the runtime side-effect and credential inventory.
2. Route known direct mutation paths through registered gateway adapters.
3. Add authenticated workload identities and remove raw agent credentials.
4. Persist grants, approvals, budgets, idempotency, and evidence transactionally.
5. Replace simulated probability claims with calibrated models or clearly named
   heuristic risk scores.
6. Run one reversible workflow in shadow, then a bounded supervised canary only
   after the documented evidence gates pass.

## Honest success criterion

Success is not “AI predicts a 0.01% failure rate.” Success is a real workflow
that produces useful customer or operational value while every consequential
action is bounded, attributable, independently auditable, reversible where
promised, and stoppable when evidence degrades.
