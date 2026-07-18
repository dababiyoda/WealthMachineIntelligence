# WealthMachine Deployment Readiness Summary

## Status: prototype / controlled-pilot preparation

The repository contains a runnable FastAPI service, database models, domain
logic, tests, container configuration, and a foundational constitutional
control plane. These assets do not establish production readiness,
enterprise-grade reliability, model accuracy, security certification, legal
compliance, or a real-world venture failure rate.

## What is currently usable

- local opportunity intake and venture assessment;
- deterministic test and demonstration workflows;
- authenticated API foundations;
- relational and in-memory graph models;
- metrics/logging foundations;
- proposal-only rule execution by default; and
- control-plane primitives for scoped grants, policy decisions, approvals,
  budgets, evidence, incidents, and execution receipts.

## Release blockers

- [x] Remove the JWT test stub; verify signature, expiry, subject, issuer,
  audience, role, and permission shape; forbid demo auth in production.
- [ ] Replace the local shared-secret reference with a production workforce IdP,
  user lifecycle/revocation, signing-key rotation, and end-to-end deployment tests.
- [ ] Inventory every consequential runtime and administrative side-effect path.
- [ ] Make gateway mediation and downstream policy unavoidable.
- [ ] Remove direct consequential credentials and unrestricted egress from agent runtimes.
- [x] Persist control state and idempotency transactionally in the local SQLite
  reference store; production still requires replication, backups, fencing, and
  downstream reconciliation.
- [ ] Anchor the Evidence Ledger outside the writer's trust domain.
- [x] Disable startup schema creation by default and forbid it in production.
- [ ] Add controlled migrations under a separate reviewed deployment identity.
- [x] Remove the unlocked schema-drop default; require explicit break-glass configuration and token.
- [ ] Enforce dual-human schema administration through the deployment identity layer.
- [ ] Validate models on representative data and calibrate any probability claims.
- [ ] Run dependency, secret, SAST, DAST, and infrastructure security reviews.
- [ ] Test backup, restore, reconciliation, incident response, pause, and kill paths.
- [ ] Complete privacy, legal, regulatory, and customer-communication review for the intended use case.
- [ ] Establish human authority coverage and approval expiry/escalation operations.

## Sample data warning

Seeded venture revenue, ROI, risk, and agent accuracy values are demonstration
fixtures. They are not observed business results or validated model metrics.

## Controlled pilot gate

A workflow may enter shadow mode only when it has a narrow charter, verified
identity, registered action definition, scoped grant, trusted adapter, complete
logging, objective outcome labels, rollback procedure, and no direct bypass.
External side effects require the additional capability-stage evidence in
`docs/PROGRESSIVE_AUTONOMY_LEVELS.md`.

## Operational references

- `docs/CONSTITUTIONAL_CONTROL_LAYER.md`
- `docs/VENTURE_CELL_CHARTER_TEMPLATE.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `docs/SIDE_EFFECT_INVENTORY.md`
