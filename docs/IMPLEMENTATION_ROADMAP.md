# Backcast GPS: Doctrine-Governed Venture Autonomy

## G — Goal

Within a credible 8–12 week pilot horizon, one Venture Cell can operate a
commercially useful digital workflow with high practical autonomy while:

- every consequential action is attributable and policy-mediated;
- each active capability has a scoped, expiring grant;
- commercial scaling and authority promotion use separate evidence;
- R3 actions require exact-intent dual human approval;
- R4 actions remain unavailable to agents;
- a critical incident pauses downstream execution quickly; and
- the entire decision and execution history can be reconstructed.

This is a target state, not an outcome guarantee. Each cycle must produce
progress, proof, correction, or protection.

## Current position

The branch containing this roadmap establishes the first software slice:

- deterministic action risk and policy decisions;
- Venture Cell charters;
- expiring, scoped capability grants and strict-subset delegation;
- execution gateway and idempotent receipts;
- aggregate grant/cell budget enforcement;
- exact-intent dual human approval for material actions;
- statistical promotion gates and automatic regression/pause;
- a hash-chained Evidence Ledger; and
- proposal-only behavior for the existing `DecisionEngine` unless a gateway is
  configured.

The first enforcement follow-up also routes the known loop, risk-manager, and
demo-monitor graph writes through registered intents. Connector mutations now
require an active allowed gateway context matching the action type and exact
venture resource; direct and confused-deputy calls fail closed in tests.

The next hardening slice removes direct AI-service SQL writes and self-minted
agent records. Synthetic market and risk artifacts are proposal-only or
gateway-mediated. Venture and agent CRUD are explicitly human-admin operations,
anonymous requests no longer default to admin, demo authentication requires an
opt-in outside production, real JWT verification binds signature/expiry/issuer/
audience and authority-claim shape, and schema auto-creation is forbidden in
production.

The current durability slice adds an optional SQLite reference store. It
reconstructs policy definitions, charters, capability grants, exact approvals,
promotion criteria, cell status, and spend counters after restart. Gateway
actions persist a reserved/in-flight/completed lifecycle: completed requests
return their prior receipt, changed fingerprints fail, and unresolved in-flight
requests require reconciliation instead of replay.

The authenticated control API reconstructs that runtime from explicit durable
paths and an authority map whose identifiers must match verified JWT subjects.
Root, human approval, read, and incident permissions are separate. Creation,
resume, termination, and revocation remain root-only; pause and approval require
a configured human; incident reports can reduce but not increase authority.
New grants are restricted to A0/A1 in the policy engine itself.

The implementation is not yet production-enforced. The durable store is local
and optional, human API identities use a shared-secret controlled-pilot
verifier, agent/workload identities are not yet cryptographically bound, the
ledger is not externally anchored, and the deployment does not yet prove that
direct credentials and network paths are absent.

## GPS lock

| Element | Lock |
| --- | --- |
| Destination | One real cell operating one R1/R2 workflow inside measured loss, scope, and recovery bounds. |
| Active node | Make gateway mediation unavoidable for every consequential production path. |
| Active gate | The complete side-effect and credential inventory is not yet known. |
| Gate-crossing evidence | Signed inventory showing 100% of consequential adapters, credentials, queues, webhooks, and egress paths are mediated or explicitly disabled. |
| Active single bottleneck metric | **Verified mediated side-effect coverage** = mediated consequential paths / inventoried consequential paths. |
| Baseline | Eleven current rule/graph action types are gateway-mediated; the static scan finds no direct agent-service SQL writes. Human-admin, offline administration, credentials, egress, and external integrations remain unresolved deployment denominators. |
| Target | 100% coverage, with a bypass test for every inventoried path. |
| Resource budget before review | One bounded integration sprint; no external customer side effects until the inventory and enforcement gate passes. |
| Review cadence | Daily during adapter migration; formal gate review before shadow and before canary. |

## Critical assumption register

| Assumption | Why it matters | Confidence | Cheapest decisive test | If false |
| --- | --- | --- | --- | --- |
| All consequential effects can be routed through a finite adapter set. | The gateway cannot govern invisible paths. | Medium | Trace code, credentials, queues, webhooks, cron jobs, and egress; execute bypass probes. | Keep affected workflow human-only or redesign the integration boundary. |
| Downstream systems can enforce scoped, short-lived credentials. | Python checks alone cannot stop direct calls. | Medium | Build one brokered token flow and attempt direct use from an agent runtime. | Keep cell at A0/A1 and select a different provider/system. |
| A representative failure taxonomy can be defined. | Trial counts are meaningless without a stable failure definition. | Medium | Label 30 historical/simulated intents with independent reviewers and reconcile disagreement. | Narrow the action until outcomes are objectively classifiable. |
| Human dual-control can meet operational latency. | R3 work stalls if approvers are unavailable. | Medium | Run approval drills with expiry and backup routing. | Reduce R3 frequency, create safer R2 templates, or remain human-operated. |
| Local control state can be upgraded to production-grade reconstructable evidence. | Promotion and incident review require trustworthy history across hosts and trust domains. | Medium | Run restore, tamper, in-flight reconciliation, and backup drills against the selected shared store; externally anchor ledger heads. | Block production canary. |

## P — Minimum sufficient stage gates

### Node 1 — Control-plane foundation

**Status:** Implemented in this branch.

- **Outcome:** Unknown and ungranted rule actions cannot cause side effects.
- **Exit evidence:** focused security tests pass; existing suite remains green;
  default `DecisionEngine` is proposal-only; documentation matches code.
- **Asset preserved if the route changes:** reusable policy, evidence, grant, and
  statistics modules.

### Node 2 — Unavoidable production enforcement

**Estimated range:** 2–4 weeks, dependent on infrastructure access.

**Status:** In progress. Known `KnowledgeGraphConnector` and AI-service writes
are mediated or proposal-only. Human CRUD is segregated behind explicit admin
authentication and tamper-evident audit. Human control operations intersect
signed permissions with a separate authority allowlist, and local transactional
state now reconstructs behind that API. Shared/replicated durability, durable
admin audit/outbox, workforce/workload identity, credentials, and deployment
egress remain open.

- Inventory every database write, message, payment, contract/signature path,
  cloud mutation, queue, webhook, and external API.
- Give cells and adapters cryptographic workload identities.
- Move consequential credentials into a broker; remove them from agent
  runtimes.
- Enforce network egress and downstream resource policy so only the gateway can
  act.
- Move the tested local policy/idempotency schema to a shared or replicated
  transactional store; add backup restore, writer fencing, and downstream
  reconciliation drills.
- Anchor ledger hashes outside the writer's trust domain.
- Exercise pause/kill and downstream credential revocation.

**Exit gate:** mediated side-effect coverage is 100%; every bypass test fails
closed; state reconstructs after restart; kill drill meets the approved recovery
objective.

**Pause:** any unknown credential, unowned adapter, or non-atomic budget path.

**Kill:** a material system cannot be mediated or stopped.

### Node 3 — One workflow in shadow

**Estimated range:** 1–2 weeks after Node 2.

- Choose one frequent, reversible R1 workflow with objective outcomes.
- Start the capability at A0/A1; do not inherit a cell-wide stage.
- Compare policy decisions and proposed actions with the approved human path.
- Run adversarial cases: prompt injection, confused deputy, replay, transaction
  splitting, stale approval, cross-cell resource, scope drift, and credential
  bypass.
- Complete at least the configured representative trial count, audit coverage,
  rollback drill, and critical red-team gate.

**Exit gate:** same-context evidence passes the A2 criterion and an independent
root human approves one-stage promotion.

**Modify:** reviewer disagreement or nonrepresentative cases.

**Regress:** any context change.

**Kill:** critical bypass, unverifiable outcomes, or unsafe rollback.

### Node 4 — Supervised canary and bounded operation

**Estimated range:** 2–4 weeks, driven by real workflow volume.

- Release to a small internal or customer cohort inside explicit loss and volume
  caps.
- Reconcile every receipt with downstream state.
- Track the failure upper bound, audit completeness, incidents, rollback time,
  support load, and policy false-positive/false-negative review.
- Independently track retained usage and unit economics for the venture-capital
  decision.
- Promote only the proven capability, one stage at a time.

**Exit gate:** assurance evidence passes A3 policy and venture evidence supports
continuation. Neither lane substitutes for the other.

### Node 5 — Portfolio operation

**Estimated range:** after at least one stable A3 capability; do not time-box
evidence maturity.

- Show grant distribution, risk tier, expiry, budget, incidents, evidence age,
  and context drift—not a misleading single cell score.
- Add independent red-team and human authority queues.
- Validate cross-cell isolation and prevent shared-memory/credential privilege
  leakage.
- Add routine regression tests whenever models, prompts, tools, policies,
  adapters, or data contracts change.

**Exit gate:** multiple cells remain isolated, observable, and individually
stoppable under live operational load.

## S — Three-step Tiny Yes system for the active node

Run this card once per consequential path:

1. **Select** — Choose one unresolved side-effect path. Name its caller,
   credential, downstream resource, maximum exposure, and current bypass route.
   Maximum scope: one adapter in one work session.
2. **Execute** — Route it through a registered action definition and gateway;
   remove direct runtime credentials/egress; add allow, deny, replay, scope,
   budget, context, and kill tests.
3. **Evidence** — Store the code/test references in the inventory, update
   mediated coverage, and choose: repeat, refine, reroute, or retire.

A checked box without an attempted bypass and downstream reconciliation does not
count.

## Validation scorecard

| Metric | Continue | Modify / pause | Kill or keep human-only |
| --- | --- | --- | --- |
| Mediated side-effect coverage | 100% before external canary | Denominator unknown or evidence incomplete | Known unmediated material path |
| Audit completeness | 100% for consequential actions | Any unexplained gap | Material action without reconstructable intent/decision/receipt |
| 95% failure upper bound | At or below stage criterion | Above criterion | Critical failure or outcome cannot be measured |
| Policy violations | 0 for promotion window | Any minor/major event triggers review/regression | Intentional or repeat critical bypass |
| Rollback / kill drill | Meets charter objective | Slow, manual, or incomplete | Cannot stop downstream execution |
| Context fingerprint | Exact match | Planned change returns to shadow | Untracked change in production |
| Venture viability | Meets node-specific paid usage/retention/economic gate | Mixed signal: narrow or revise | Exceeds capital/time cap without external proof |

## What not to build yet

- a broad autonomous child-agent marketplace;
- a single “AI confidence” authority score;
- automatic promotion from revenue or retention;
- a portfolio dashboard before the underlying evidence and identity are durable;
- high-consequence connectors with raw long-lived credentials; or
- claims of legal, regulatory, or security compliance based on this repository
  alone.
