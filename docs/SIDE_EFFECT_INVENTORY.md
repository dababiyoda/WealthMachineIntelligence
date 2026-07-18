# Consequential Side-Effect Inventory

**Snapshot:** 2026-07-18 static repository scan
**Purpose:** Define the denominator for verified gateway coverage. This is a
code inventory, not proof of deployed credentials, queues, webhooks, cron jobs,
or network routes.

## Runtime paths

| Caller | Effect | Nominal tier | Current enforcement | Required next move |
| --- | --- | ---: | --- | --- |
| `services/decision_engine.py` | Update venture status; route review, funnel, and compliance notifications. | R1 | **Gateway-only in code; proposal-only by default.** Connector calls require an active allowed intent for the exact action/resource. | Give the connector a gateway-only deployment identity and test downstream credential bypass. |
| `core/loops.py` | Persist derived opportunity, market-alignment, and ROI metrics. | R1 | **Gateway-mediated; proposal-only without a gateway.** Uses `persist_venture_opportunities` and `persist_venture_metrics`. | Reconcile receipts with durable downstream state and independently classify provenance. |
| `services/risk_management.py` | Persist heuristic risk assessment. | R1 | **Gateway-mediated; proposal-only without a gateway.** Heuristic provenance and uncalibrated status are retained. | Split append-only assessment evidence from mutable venture state in the durable schema. |
| `services/market_monitor.py` | Persist randomized/demo metrics on a schedule. | R1 | **Gateway-mediated; proposal-only by default.** Payload is marked `randomized_demo_simulation` and not production evidence. | Keep disabled in production or isolate in a demo cell with shadow-stage grants. |
| `services/ai_agents.py:MarketIntelligenceService` | Persist synthetic market analysis. | R1 | **Gateway-mediated; proposal-only by default.** Uses `persist_market_analysis` and labels randomized output non-production evidence. | Replace simulation with validated sources before it enters an evidence promotion lane. |
| `services/ai_agents.py:RiskAssessmentService` | Read venture state and request risk-assessment persistence. | R1/R2 if used for capital decisions | **Read-only analysis plus gateway intent.** It no longer writes venture/assessment rows directly and cannot create an agent record. Persistence requires a root-provisioned agent ID. | Split append-only assessment evidence from mutable venture state in the durable schema. |
| Retired: `services/ai_agents.py:_get_agent_id` | Previously created a persistent agent record during risk analysis. | R2 | **Removed.** Analysis cannot mint a persistent identity or authority record. | Provision workload and database identities through the human/root administration process. |
| `api/routes/ventures.py` | Create, update, discontinue, and launch venture records. | Human administrative plane | **Signed admin JWT required; anonymous and ordinary users fail closed.** Signature, expiry, issuer, audience, role, and permission shape are checked. Each mutation writes a hash-chained intent/outcome audit pair. | Replace the shared-secret reference with a workforce IdP and account revocation; make audit/outcome transactional and use field-specific dual control where material. |
| `api/routes/agents.py` | Activate/deactivate persistent agent records. | Human administrative plane | **Signed admin JWT required with hash-chained audit.** `is_active` does not create a capability grant. | Add workforce identity lifecycle/key rotation and a durable transactional audit/outbox. |
| `api/routes/control.py` | Create/pause/resume/terminate cells; issue/revoke grants; record approvals/incidents. | Constitutional human control plane | **Verified subject plus independently configured authority and exact control permission.** New grants are A0/A1 only; actor identity and TTLs are server-bound; every policy mutation enters the durable control snapshot and Evidence Ledger. | Move the runtime to a replicated store, workforce identity, and independently anchored evidence before production. |
| `api/routes/opportunities.py` | Evaluate and retain in-memory assessment objects. | R0/R1 | Explicitly recommendation-only. | Add durable evidence provenance; never convert an assessment directly into an execution grant. |
| `auth/keycloak.py` | Fetch JWKS for token verification. | R0 external read | Direct network read. | Pin issuer/audience, cache safely, and allowlist egress; no venture capability needed. |
| `control/evidence.py` | Append control evidence to JSONL. | Trusted control write | Inside control plane. | Move to transactional, independently anchored storage with separate auditor access. |
| `control/state_store.py` | Persist policy snapshots and gateway action lifecycle in SQLite. | Trusted control write | Integrity-hashed, schema-versioned, transactional local store with fail-closed in-flight recovery. | Move to a replicated production store; add backups, writer fencing, external anchoring, and downstream reconciliation. |

## Administrative paths

These are not Venture Cell autonomy paths, but deployment roles must prevent an
agent identity from reaching them:

| Path | Effect | Required role |
| --- | --- | --- |
| `setup_database.py`, `database/init_db.py` | Seed ventures and agents. | Offline deployment administrator. |
| `database/connection.py:create_tables` | Create schema. | Migration identity. |
| `database/connection.py:drop_tables` | Destructive schema removal. | Requires explicit `ALLOW_SCHEMA_DROP=true` plus a constant-time confirmation token; keep callable only by an offline break-glass identity. Dual-human workflow remains a deployment requirement. |
| `api/main.py` startup | Schema creation is disabled by default and forbidden in production. | Add controlled, reviewed migration tooling under a separate identity. |
| `api/control_runtime.py` startup | Reconstruct the root/human authority map, policy snapshot, action lifecycle, and ledger. | Production requires explicit paths and at least two distinct configured human subjects; shared-store migration remains open. |

## Common choke point

`KnowledgeGraphConnector` centralizes several graph/database mutations. Its
mutation methods now require a short-lived authorization context installed only
while `ExecutionGateway` invokes an allowed adapter. The context binds action
type and exact venture resource; direct calls and confused-deputy calls fail
before mutation. This is useful in-process defense in depth, not a cryptographic
security boundary. Production must still place the connector behind a workload
identity, credential broker, and network policy unavailable to agent processes.

## Coverage accounting

Eleven current action types are mediated in code: four rule actions and seven
knowledge-graph persistence actions. The scanned agent services contain no
remaining direct SQL write call. Human-administrator CRUD, offline database
administration, deployment configuration, and external connectors are separate
denominators and are not yet production-proven. Therefore the honest baseline
is:

- **Code-mediated agent actions:** eleven registered action types, with connector bypass tests;
- **Known agent-service direct SQL write families:** zero in this static scan;
- **Human-admin direct database families:** two, role-gated and hash-chain audited but not transactionally coupled;
- **Deployment credential/egress coverage:** unverified; and
- **Verified mediated side-effect coverage:** not yet reportable as a percentage.

Claim 100% only after runtime tracing, credential inventory, queue/webhook/cron
inventory, downstream reconciliation, and attempted bypass tests agree with the
code inventory.
