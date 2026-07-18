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
| `services/ai_agents.py:MarketIntelligenceService` | Insert market-analysis database records. | R1 | Direct database transaction. | Route through evidence persistence with provenance; remove production claims from simulated model outputs. |
| `services/ai_agents.py:RiskAssessmentService` | Insert risk assessment and mutate venture risk fields. | R1/R2 if used for capital decisions | Direct database transaction. | Split append-only assessment from venture-state mutation; require policy for the latter. |
| `services/ai_agents.py:_get_agent_id` | Create persistent agent identity record. | R2 | Direct database transaction. | Move identity provisioning to root-human control; do not let an agent mint its own persistent authority. |
| `api/routes/ventures.py` | Create, update, soft-delete/restore, and change venture state. | R1–R3 by payload | Authenticated API, outside cell policy. | Separate human-admin route from agent route; route agent calls through registered intents and classify fields. |
| `api/routes/agents.py` | Activate/deactivate or update persistent agents. | R3/R4 when authority changes | Authenticated API, outside cell policy. | Restrict to root-human administration and ledger every authority-impacting change. |
| `api/routes/opportunities.py` | Evaluate and retain in-memory assessment objects. | R0/R1 | Explicitly recommendation-only. | Add durable evidence provenance; never convert an assessment directly into an execution grant. |
| `auth/keycloak.py` | Fetch JWKS for token verification. | R0 external read | Direct network read. | Pin issuer/audience, cache safely, and allowlist egress; no venture capability needed. |
| `control/evidence.py` | Append control evidence to JSONL. | Trusted control write | Inside control plane. | Move to transactional, independently anchored storage with separate auditor access. |

## Administrative paths

These are not Venture Cell autonomy paths, but deployment roles must prevent an
agent identity from reaching them:

| Path | Effect | Required role |
| --- | --- | --- |
| `setup_database.py`, `database/init_db.py` | Seed ventures and agents. | Offline deployment administrator. |
| `database/connection.py:create_tables` | Create schema. | Migration identity. |
| `database/connection.py:drop_tables` | Destructive schema removal. | Break-glass human dual control; unavailable to application/agent identities. |
| `api/main.py` startup | Calls schema creation. | Remove from production runtime; use migrations. |

## Common choke point

`KnowledgeGraphConnector` centralizes several graph/database mutations. Its
mutation methods now require a short-lived authorization context installed only
while `ExecutionGateway` invokes an allowed adapter. The context binds action
type and exact venture resource; direct calls and confused-deputy calls fail
before mutation. This is useful in-process defense in depth, not a cryptographic
security boundary. Production must still place the connector behind a workload
identity, credential broker, and network policy unavailable to agent processes.

## Coverage accounting

Ten current action types are mediated in code: four rule actions and six
knowledge-graph persistence actions. The complete production denominator is
still unknown because direct SQL paths, deployment configuration, and external
connectors are not fully mediated or represented by this static scan. Therefore
the honest baseline is:

- **Code-mediated:** ten registered action types, with connector bypass tests;
- **Known direct runtime mutation families:** at least five in the table above;
- **Deployment credential/egress coverage:** unverified; and
- **Verified mediated side-effect coverage:** not yet reportable as a percentage.

Claim 100% only after runtime tracing, credential inventory, queue/webhook/cron
inventory, downstream reconciliation, and attempted bypass tests agree with the
code inventory.
