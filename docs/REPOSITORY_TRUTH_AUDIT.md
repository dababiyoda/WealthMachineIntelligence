# UAT Repository Truth Audit

## Decision

The repository is a **governed-preview implementation with a durable owner-beta
website**, not a complete autonomous venture institution or a public commercial
SaaS. The canonical release path is `main.py` -> `src.api.main` ->
`src.governance`. Legacy agents, simulations, historical assets, and the nested
enhanced prototype remain useful reference material, but they are not the
production authority boundary.

This audit prevents plans, fixtures, simulations, or persuasive model output
from being presented as implemented capability.

## Audit method and inventory

The audit covered all 210 release-candidate files, repository tests, executable entry
points, API routes, governance schemas, legacy agent and loop packages,
documentation, workflows, container artifacts, and the published ChatGPT Site.
It also inspected the sibling GitHub repository
`dababiyoda/DALEOBANKS` at commit
`1bd7da1ca72e4665509bdabf4269896dea76e2bf`.

Forty-three compiled Python cache files are still tracked. They are ignored for
future changes but remain repository-hygiene debt until deliberately removed in
a scoped cleanup.

## Claim-to-code map

| Area | Status | Evidence | Boundary |
| --- | --- | --- | --- |
| UAT constitution and schemas | Implemented | `spec/uat/v1/`, schema tests | Normative draft; independent AG0 review remains open |
| Governance record API | Implemented preview | `src/governance/`, `/api/v1/governance` | Records and evaluates authority; performs no external action |
| Evidence and decision reconstruction | Implemented preview | claims, evidence, decisions, approvals, executions, outcomes, audit chain | Application-enforced hash chain is not independently anchored |
| Opportunity compatibility intake | Implemented preview | `/api/opportunities/intake`, contract tests | Held assessment only; production token fails closed |
| Legacy eight-agent and loop system | Simulation/reference | `src/agents/`, `src/loops/`, `src/network_wealth_engine.py` | Deterministic heuristics and fixtures are not market proof |
| Risk scores and forecasts | Simulation/reference | legacy risk and performance modules | Uncalibrated indices; not probabilities or financial advice |
| AI integration architecture | Planned/reference | `ai_integration/` documentation and placeholders | No production agent runtime, broker, or tool gateway |
| Enhanced nested prototype | Incomplete/superseded | `WealthMachineIntelligenceEnhanced/` | Excluded from the canonical package and release path |
| ChatGPT Site owner beta | Implemented bounded product surface | deployed Site, D1 schema, authenticated owner routes, rendered tests | Owner-only; no public customers, charges, OAuth, secrets, or external actions |
| Multi-tenant subscription SaaS | Planned | commercial backcast and readiness record | Billing, entitlements, public access, and two-identity isolation not proven |
| Venture Pods and recursive workers | Planned | enterprise specification | No isolated runtime or delegated execution authority exists |

## DALEOBANKS sibling-service boundary

DALEOBANKS is a separate GitHub service, not a Site connector card pretending
to be a live integration. Its repository already contains a compatible
schema-1.0 `OpportunityPacket` sender, an HTTP/mock WealthMachine client, and
tests that preserve `requires_human_approval=true`. UAT contains the receiving
compatibility endpoint.

A separate hardening candidate now adds authenticated control and WebSocket
boundaries, production configuration fail-closed checks, dependency repairs,
and CI coverage. Those changes passed local verification but are not a merged
or deployed production service, so they do not increase DALEOBANKS authority.

That proves a versioned **contract boundary**, not a production connection.
Activation remains held until both services demonstrate:

1. approved runtime endpoints and service ownership;
2. scoped, rotated service credentials outside model and browser context;
3. durable idempotency, delivery, receipt, and reconciliation records;
4. replay, rate-limit, timeout, retry, and schema-drift handling;
5. human approval and independently verified final state;
6. incident containment, recovery, and contract-version rollback.

The selected Library folder `/DALEOBANKS` may contain supplementary owner
material. Its contents were not readable through the Library surface available
in this run, so no claim depends on it.

## LIVE PLAYER context boundary

LIVE PLAYER is an AI-agent context source, not a provider connection, tool,
identity, or grant of authority. The selected Library folder `/LIVE PLAYER`
could not be listed or materialized through the read surface available in this
run. It is therefore recorded as `unresolved`, not absent.

Before any LIVE PLAYER content enters an agent context, it must be:

- materialized from the authorized Library source;
- hashed, versioned, attributed, and classified;
- screened as untrusted content for prompt injection and secrets;
- scoped to one account, Egregore, role, and purpose;
- separated from system policy, credentials, permissions, and tool authority;
- activated by a human with an expiry and revocation path;
- logged so an outcome can be reconstructed against the exact context version.

Context may influence a bounded recommendation. It can never authorize an
action, modify the constitution, grant a capability, or prove an external fact.

## Test evidence

- WealthMachine canonical suite: 94 passing tests.
- DALEOBANKS Python suite: 264 passing tests, including lazy provider startup,
  authenticated WebSocket identity,
  and fallback coverage under the workspace proxy configuration.
- ChatGPT Site: lint, build, rendered HTML checks, and D1-compatible Node tests
  passed for the deployed owner-beta checkpoint.
- DALEOBANKS frontend: clean locked install, TypeScript check, production build,
  and production dependency audit completed; the audit reported zero known
  vulnerabilities at the configured threshold.

## Highest-priority blockers

1. The DALEOBANKS hardening candidate must be reviewed, merged, deployed, and
   reverified before any live bridge is considered.
2. The Site host currently lacks a supported public/customer access mode, so a
   self-serve commercial launch is unavailable.
3. Subscription price, legal entity, terms, payment provider, webhook
   entitlement, tax, refund, and support ownership are unapproved or absent.
4. Multi-identity tenant isolation has not been demonstrated.
5. LIVE PLAYER context remains unread and must stay quarantined.
6. No paid minimum-value event, retention evidence, independent security
   assessment, or recovery exercise has cleared the scale gates.

## Truth rule

Every customer-facing or operator-facing claim must resolve to one of:
`implemented`, `preview_only`, `planned`, `superseded`, `blocked`, or `absent`.
An estimate, score, fixture, draft, context item, request, or compatibility
contract must never be silently promoted to verified outcome, active
entitlement, live connection, or execution authority.
