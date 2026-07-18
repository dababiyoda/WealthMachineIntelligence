# Constitutional Control Layer

## Purpose

The control layer is the non-agent authority boundary for Venture Cells. It
decides whether an action may occur; the model only proposes an intent. The
layer is deterministic, fail-closed, independently configured, and unable to be
weakened through an ordinary agent action.

This implementation is a foundation, not a claim of production certification.

## Components

| Component | Responsibility | Current module |
| --- | --- | --- |
| Action registry | Assign immutable risk and minimum-stage policy to action types. | `src/control/defaults.py` |
| Cell charter | Bound mission, geography, data class, prohibited actions, budget, owner, and kill conditions. | `VentureCellCharter` |
| Capability grant | Lease action authority to an agent for resources, parameters, context, time, and budget. | `CapabilityGrant` |
| Policy decision point | Return allow, shadow, review, or deny with reason codes. | `src/control/policy_engine.py` |
| Execution gateway | Enforce idempotency, invoke trusted adapters only after allow, and produce receipts. | `src/control/gateway.py` |
| Durable control state | Transactionally persist policy snapshots and the reserved/in-flight/completed action lifecycle for restart recovery. | `src/control/state_store.py` |
| Authorized execution context | Bind the allowed intent's action and resource to the adapter call stack; reject ordinary direct or confused-deputy mutation calls. | `src/control/execution_context.py` |
| Graph adapters | Convert loop, risk, and monitor persistence requests into intents and dispatch validated payloads only inside the gateway. | `src/control/graph_adapter.py` |
| Evidence Ledger | Append hash-chained intents, policy decisions, approvals, grants, incidents, promotions, regressions, and receipts. | `src/control/evidence.py` |
| Assumption Register | Version critical assumptions and require external/human evidence plus independent verification for terminal conclusions. | `src/control/assumptions.py` |
| Promotion evaluator | Apply exact statistical assurance gates independent of commercial metrics. | `src/control/promotion.py` |

## Enforcement sequence

For every consequential action, the gateway:

1. receives an immutable `ActionIntent`;
2. records a digest of the payload rather than raw sensitive content;
3. durably reserves the action ID and rejects reuse with another fingerprint;
4. returns the prior receipt when the same completed action is retried;
5. asks the policy engine to evaluate a new or still-reserved intent;
6. performs no side effect for shadow, review, or deny;
7. fails closed if no trusted executor is registered;
8. atomically marks the action in flight before invoking an adapter;
9. binds the allowed action and resource to a short-lived execution context;
10. invokes the adapter after allow and clears that context afterward;
11. records spend only after successful execution; and
12. durably completes the action with a result digest, external reference, and
    execution receipt.

The policy engine checks, in order:

- trusted action definition and risk tier;
- active cell and current charter policy version;
- permanent and charter prohibitions;
- cell geography and data scope;
- active, unexpired grant for the same cell, agent, action, and resource;
- exact execution-context fingerprint;
- grant geography, data, and parameter scope;
- minimum capability stage;
- per-action, daily, total, grant, and cell budgets; and
- distinct, unexpired, exact-intent human approvals when required.

Unknown action, missing state, stale context, and adapter absence never default
to allow.

## Restart recovery and transaction boundary

`SQLiteControlStateStore` is the capital-light reference implementation for a
single control-plane process. It stores a versioned, integrity-hashed
snapshot of action definitions, charters, grants, approvals, promotion rules,
cell/grant spend counters, and status. It separately stores each gateway action
as `reserved`, `inflight`, or `completed`.

On restart:

- a completed action returns its original decision and receipt without invoking
  the adapter again;
- a reserved action may be reevaluated after an approval, promotion, or trusted
  adapter bootstrap;
- an in-flight action is denied with
  `reconciliation_required_for_inflight_action`; it is never blindly replayed;
- a changed action fingerprint is denied; and
- a snapshot or action-record hash mismatch raises an integrity error before
  authority is reconstructed.

Each policy snapshot also records an Evidence Ledger sequence/hash anchor.
Authority-reducing controls and bounded execution can recover without the old
ledger file, but capability promotion fails closed until the anchored chain is
reconstructed and verified. Configure a durable `EvidenceLedger` path alongside
the state store if promotions must remain available after restart.

The store uses SQLite WAL mode, full synchronous writes, and immediate
transactions. This gives local restart durability, not a distributed exactly-
once guarantee. The transaction cannot atomically commit both an arbitrary
downstream side effect and the local receipt. An in-flight record therefore
represents an uncertain outcome that an operator must reconcile with the
downstream system. Production still needs a shared/replicated store, fencing or
single-writer leadership, transactional outbox/inbox patterns where available,
backups, and explicit reconciliation procedures.

The hashes detect corruption and unsynchronized edits; they are not keyed and
do not stop an attacker who can rewrite both a record and its hash. Protect the
database with operating-system access controls and add independent/WORM
anchoring in production.

## Approval binding

An approval is bound to the hash of:

- action ID;
- cell and agent identity;
- action type and resource;
- complete payload;
- monetary amount;
- geography and data classes; and
- execution-context fingerprint.

It is also bound to a policy version and expiry. Changing any consequential
field invalidates the approval. R3 defaults require two distinct registered
human identities.

## Identity and credential requirements

The Python layer cannot, by itself, prevent a process from calling an external
API directly. Production deployment therefore must:

- give each human, agent, cell, and service a distinct workload identity;
- keep payment, communications, cloud, and signing credentials in a broker;
- issue short-lived tokens scoped to one approved adapter operation;
- block direct agent-runtime egress to consequential systems;
- enforce the same amount, account, tenant, recipient, and resource constraints
  in the downstream system where possible; and
- make the gateway the only network identity trusted by those systems.

Until those controls exist, a workflow with raw credentials remains at A0/A1
regardless of Python policy results.

## Human administration plane

Venture CRUD and agent-record activation are not agent autonomy paths. They now
require an explicitly authenticated user with the `admin` role and permission;
missing credentials never default to an administrator. Local demo identities
are disabled unless `ALLOW_DEMO_AUTH=true`, and that setting is rejected in
production. The reference verifier checks a fixed algorithm, signature, expiry,
subject, issuer, audience, and the signed role/permission shape; arbitrary
bearer strings and tokens for another service fail closed. Each mutation records
an intent/outcome pair in a separate hash-chained admin ledger.

An `AIAgent.is_active` database flag is operational metadata, not a capability
grant. Only the root-controlled policy engine can issue action authority. The
current admin ledger is not transactionally coupled to the database and remains
tamper-evident rather than independently anchored, so production still requires
a workforce identity provider with account lifecycle and signing-key rotation,
plus a durable audit/outbox design. The HS256 verifier is a controlled-pilot
reference, not a substitute for that identity system.

## Evidence Ledger guarantees and limits

The ledger is append-only through its public API and every entry includes the
previous hash. `verify_chain()` detects reordered, deleted, or modified entries.
When a JSONL path is configured, each append is flushed and `fsync`ed.

This is **tamper-evident, not tamper-proof**. A production ledger must add:

- transactional persistence;
- immutable/WORM retention;
- external timestamp or hash anchoring;
- backup and reconstruction tests;
- access separation between writers and auditors;
- schema versioning and retention rules; and
- data minimization for regulated or sensitive content.

## Context fingerprint

Every grant binds to a fingerprint representing the relevant model, prompt,
tools, policy, data contract, adapter version, and other behavior-changing
configuration. A mismatch returns `shadow`, even if all business metrics are
healthy. A changed context is a new assurance claim and must be revalidated.

## Child delegation

Delegation is allowed only for R0–R2 grants with remaining delegation depth.
The grantee may create a child grant only when it:

- stays in the same cell and action type;
- targets a different child identity;
- expires no later than its parent;
- has a lower delegation depth;
- does not increase stage or any budget;
- remains inside resource, geography, data, and parameter scopes; and
- narrows at least one dimension.

R3 material authority and all R4 authority are non-delegable.

## Integration with the existing rule engine

`DecisionEngine` is now proposal-only when no gateway is configured. It no
longer mutates venture status or notifies roles by default. With a configured
gateway, a matching rule creates an `ActionIntent`; only a valid cell grant can
reach the existing connector adapter.

The Income Streams Loop, risk manager, and demo market monitor follow the same
rule for graph persistence. Without a gateway they return explicit proposals
and perform no connector mutation. With a gateway, their registered persistence
actions require separate capability grants. This closes ordinary in-process
bypass routes but does not replace production process/credential isolation.

Example bootstrap:

```python
from datetime import timedelta
from decimal import Decimal

from src.control import (
    AutonomyStage,
    CapabilityGrant,
    EvidenceLedger,
    SQLiteControlStateStore,
    VentureCellCharter,
    build_default_control_plane,
)
from src.control.models import utc_now

policy, gateway = build_default_control_plane(
    root_actor_id="operator-1",
    human_authorities={"reviewer-1", "reviewer-2"},
    evidence_ledger=EvidenceLedger("var/control/evidence.jsonl"),
    state_store=SQLiteControlStateStore("var/control/control.db"),
)
policy.create_cell(
    "operator-1",
    VentureCellCharter(
        cell_id="venture-42",
        mission="Validate one approved workflow",
        owner_id="operator-1",
        allowed_geographies=frozenset({"US"}),
        allowed_data_classes=frozenset({"public"}),
        max_daily_spend_usd=Decimal("25"),
        max_total_spend_usd=Decimal("100"),
    ),
)
policy.issue_grant(
    "operator-1",
    CapabilityGrant(
        grant_id="grant-42-status",
        cell_id="venture-42",
        agent_id="decision-engine",
        action_type="update_venture_status",
        stage=AutonomyStage.SUPERVISED_CANARY,
        resource_prefixes=("venture:venture-42",),
        parameter_constraints={
            "parameters.new_status": ("Needs Review", "On Hold"),
        },
        expires_at=utc_now() + timedelta(hours=8),
        context_fingerprint="model-v1:prompt-v3:tools-v2",
        allowed_geographies=frozenset({"US"}),
        allowed_data_classes=frozenset({"public"}),
    ),
)
```

## Production release gates

Do not label the system doctrine-enforced in production until:

- every consequential adapter is inventoried and gateway-mediated;
- agent runtimes lack direct consequential credentials and egress;
- policy, grants, approvals, spend counters, and idempotency use a production
  shared/replicated transactional store with tested restore and reconciliation;
- identities are cryptographically authenticated, not caller-supplied strings;
- the ledger is independently anchored and reconstructable;
- pause/kill is tested against real dependencies;
- red-team bypass tests pass; and
- an on-call human authority workflow is operational.
