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
| Evidence Ledger | Append hash-chained intents, policy decisions, approvals, grants, incidents, promotions, regressions, and receipts. | `src/control/evidence.py` |
| Assumption Register | Version critical assumptions and require external/human evidence plus independent verification for terminal conclusions. | `src/control/assumptions.py` |
| Promotion evaluator | Apply exact statistical assurance gates independent of commercial metrics. | `src/control/promotion.py` |

## Enforcement sequence

For every consequential action, the gateway:

1. receives an immutable `ActionIntent`;
2. records a digest of the payload rather than raw sensitive content;
3. rejects reuse of an action ID with a different fingerprint;
4. asks the policy engine to evaluate the intent;
5. performs no side effect for shadow, review, or deny;
6. fails closed if no trusted executor is registered;
7. invokes the adapter once after allow;
8. records spend only after successful execution; and
9. stores a result digest and external reference in an execution receipt.

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

Example bootstrap:

```python
from datetime import timedelta
from decimal import Decimal

from src.control import (
    AutonomyStage,
    CapabilityGrant,
    VentureCellCharter,
    build_default_control_plane,
)
from src.control.models import utc_now

policy, gateway = build_default_control_plane(
    root_actor_id="operator-1",
    human_authorities={"reviewer-1", "reviewer-2"},
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
- policy, grants, approvals, spend counters, and idempotency are transactional;
- identities are cryptographically authenticated, not caller-supplied strings;
- the ledger is independently anchored and reconstructable;
- pause/kill is tested against real dependencies;
- red-team bypass tests pass; and
- an on-call human authority workflow is operational.
