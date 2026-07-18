# UAT Commercial Platform Backcast

## Decision

Build the commercial product as a staged, multi-tenant **Egregore workspace**
around the governed UAT core. Do not connect money, production tools, customer
data, or DALEOBANKS execution until the control, identity, tenant-isolation,
billing, and external-state verification gates for that capability have passed.

An Egregore is a user-owned, governed UAT workspace. It is not an autonomous
legal person, an unrestricted agent swarm, or a promise that a venture will
succeed. It contains a mission, membership boundary, evidence state, authority
ceiling, subscription state, integration registry, and auditable operating
history.

This document applies Backcast GPS and a Deep Strategic Tree Search to the
commercial objective. Its score of process completeness is not a probability
of commercial success.

## Reasoning summary

### Current reality

- The repository implements a bounded AG1/AG2 governed-preview candidate and a
  truthful, owner-only ChatGPT Site.
- The Site uses ChatGPT-managed identity and now has a D1-backed owner-beta
  account, Egregore, membership, subscription-intent, connector-intent,
  agent-context-intent, and audit model. It has no verified customer tenant,
  active subscription
  entitlement, provider webhook, external OAuth connector, or live
  control-plane connection.
- The FastAPI preview and the ChatGPT Site are separate deployments.
- DALEOBANKS is a separate GitHub service. Both repositories implement a
  compatible schema-1.0 opportunity intake contract that fails closed in
  production and always requires human approval. No production endpoint,
  scoped credential, durable reconciliation, or live execution is configured.
- LIVE PLAYER is an AI-agent context source in the selected ChatGPT Library,
  not a connector or authority grant. Its contents remain unresolved because
  the required Library read/materialization surface was unavailable.
- The current Sites workspace offers owner/custom or workspace-wide access; it
  does not currently offer public-internet access.

### Control layer

The deepest current constraint is **trusted commercial identity and settlement**:
the product cannot safely sell or operate user-specific venture work until it
can bind a verified user to an isolated workspace, a verified subscription, an
explicit connector grant, a bounded action, and a reconciled external result.

### Strongest counterexample

A polished pricing page and hosted checkout could collect money quickly, but it
would sell access to capabilities the product cannot yet deliver to multiple
isolated customers. That route increases refund, privacy, support, legal, and
reputation risk faster than it creates product proof.

## GPS lock

- **Destination:** paying customers can sign in, create an isolated Egregore,
  activate a monthly plan, connect explicitly authorized providers, and run
  governed workflows whose real capabilities and limits are visible.
- **Current position:** owner-only governed website with durable owner product
  state; no active subscription, customer-access mode, production connector,
  LIVE PLAYER context ingestion, or control-plane client.
- **Active node:** owner-beta acceptance followed by closed multi-user beta.
- **Active gate:** signed-in persistence is implemented, but customer access
  and two-real-identity tenant isolation cannot yet be demonstrated.
- **Gate-crossing evidence:** a real signed-in owner retrieves durable state
  across sessions; then two invited identities can access only explicitly
  authorized Egregores while anonymous, revoked, guessed-ID, and cross-tenant
  access fail closed. The UI must never present an intent as a live connection,
  payment, or loaded context.
- **Active single bottleneck metric:** protected durable product workflows
  passing identity and ownership tests.
- **Baseline:** 0.
- **Target:** 6 workflows: provision account, create Egregore, retrieve owned
  Egregore, request plan activation, request a connector, and request bounded
  agent-context activation.
- **Resource budget:** no customer funds, production credentials, external
  writes, public access widening, or sensitive data during this node.
- **Three-step system:** select one ownership workflow; implement the smallest
  server-enforced path; prove persistence and isolation before adding another.
- **Review cadence:** after each hosted checkpoint and whenever access,
  billing, credential, or external-action authority changes.

## Critical assumption register

| Assumption | Why it matters | Current confidence | Decisive test | If false |
| --- | --- | --- | --- | --- |
| ChatGPT Sites identity is stable enough to key an account | Every ownership check depends on it | Medium | Persist and retrieve an account across signed-in sessions | Add a separate reviewed identity provider before beta |
| Sites D1 supports the required durable tenant records | The website needs authoritative product state | Medium | Apply migrations and pass deployed create/read ownership tests | Keep Site presentation-only and deploy a separate backend |
| Public or customer-specific access can be enabled lawfully | Self-serve subscriptions require customer access | Low | Obtain a supported access mode and test a non-owner beta user | Use an approved external app host or closed workspace beta |
| A monthly plan will create paid demand | Billing is not demand proof by itself | Low | Obtain paid, retained founding customers under explicit terms | Revise buyer, offer, price, or product before scaling |
| DALEOBANKS can operate as an authorized production sibling service | Schema-1.0 compatibility exists, but runtime authority and reconciliation do not | Medium-low | Configure a sandbox endpoint, scoped credential, idempotency, receipt, replay, failure, and reconciliation tests | Keep the adapter held and use file/manual intake |
| LIVE PLAYER content is safe and useful for a bounded role | Context can contain stale, private, conflicting, or hostile instructions | Unknown | Materialize the authorized source, hash and classify it, scan it as untrusted input, and run a no-tools shadow evaluation | Keep the context unresolved and do not load it |
| External providers permit the intended OAuth scopes and data use | Connector cards do not create legal access | Low | Register applications and complete provider review and consent tests | Reduce scopes, use imports, or remove the provider |

## Route tournament

Scores are comparative design aids from 0 to 100, not outcome probabilities.

| Route | Mechanism | Score | Evidence confidence | Fatal risk | Disposition |
| --- | --- | ---: | --- | --- | --- |
| Fast facade | Public landing page plus payment link before product state | 54 | Low | Charges users for an unproven, inaccessible product | Reject |
| Full autonomous SaaS now | Build billing, OAuth, runtime, tools, pods, and portfolio control at once | 43 | Low | Unbounded scope hides failed isolation and authority assumptions | Reject |
| Governed staged hybrid | Durable owner beta, closed paid proof, connector-by-connector activation, then bounded operations | 88 | Medium | May be slower than a facade, but preserves trust and assets | Select |
| External-hosted control plane first | Move all product work to a conventional SaaS host before validating the Site experience | 68 | Medium | Higher initial cost and delays product-learning proof | Preserve as hedge |

The selected sequence is:

`owner beta -> isolated Egregore -> paid closed beta -> verified connectors -> DALEOBANKS sandbox -> reconciled bounded actions -> wider commercial access`

## Backcasted success state

### Completion conditions

1. Each user has a verified identity and belongs only to explicitly authorized
   Egregores.
2. Every Egregore has a mission, charter, risk posture, authority ceiling,
   subscription entitlement, and audit history.
3. A payment provider verifies recurring status through a signed webhook;
   entitlement never depends on a browser claim or redirect alone.
4. Every connector uses provider-issued consent, minimum scopes, encrypted
   server-side tokens, expiry, revocation, and data-classification controls.
5. The website reaches the UAT control plane through a mediated, authenticated,
   idempotent gateway; it never receives a broad production credential.
6. DALEOBANKS passes a sandbox contract, replay, reconciliation, failure, and
   human-approval test before any production action.
7. At least one real customer pays, reaches a minimum value event, and retains
   under documented terms without relying on hidden founder execution.
8. Restore, incident, privacy, legal, support, refund, and kill procedures have
   named human owners and demonstrated evidence.

### Falsification

Pause or redesign the commercial route if the platform cannot provide
customer-appropriate access, tenant isolation cannot be demonstrated, the
payment provider cannot produce authoritative entitlement events, users do not
reach a measurable value event, or the required connector permissions cannot
be obtained lawfully.

## Stage-gated plan

### Node 0 — Repository truth audit

- **Outcome:** every material claim is mapped to implemented, preview-only,
  planned, superseded, or absent.
- **Exit evidence:** inventory, executable checks, and current-capability record
  agree.
- **Kill threshold:** any customer-facing claim exceeds demonstrated behavior.

### Node 1 — Durable owner beta

- **Outcome:** signed-in owner can create and retrieve an isolated Egregore,
  plan intent, connector intents, and an unresolved agent-context intent.
- **Exit evidence:** D1 migration, authenticated APIs, ownership checks,
  rendered interaction tests, and deployed persistence proof.
- **Authority ceiling:** no billing charge, OAuth token, control-plane mutation,
  or external side effect.

### Node 2 — Closed multi-user beta

- **Outcome:** invited users receive explicit memberships and cannot cross
  tenant boundaries.
- **Exit evidence:** invitation, revocation, role, object-level authorization,
  enumeration, and backup-isolation tests with at least two real identities.
- **Pause threshold:** customer access remains unavailable in the host policy.

### Node 3 — Subscription activation

- **Outcome:** one approved monthly plan grants an entitlement only after a
  signed provider event.
- **Exit evidence:** approved price and terms; test checkout; webhook signature,
  replay, ordering, cancellation, refund, grace-period, and reconciliation
  tests; tax and support owners.
- **Kill threshold:** payment state can be forged or cannot be reconciled.

### Node 4 — Connector activation

- **Outcome:** one provider at a time moves from requested to connected after
  reviewed OAuth and data controls.
- **Exit evidence:** least scopes, consent, short-lived or rotated tokens,
  encrypted server storage, revoke path, provider sandbox, audit, and egress
  tests.
- **Kill threshold:** a model, browser, or client can retrieve a raw secret.

### Node 5 — DALEOBANKS sandbox bridge

- **Outcome:** a versioned adapter exchanges bounded opportunity records in a
  non-production environment.
- **Exit evidence:** contract tests, authentication, idempotency, rate limits,
  replay defense, human approval, independent final-state verification, and
  failure recovery.
- **Kill threshold:** schema ownership, legal authority, or reconciliation is
  unresolved.

### Node 6 — One paid Venture Pod

- **Outcome:** a customer reaches a defined minimum value event through a
  bounded, supportable workflow.
- **Exit evidence:** payment, delivery, verified customer outcome, gross-margin
  range, incident record, and retention decision.
- **Scale threshold:** a second customer can be served without rebuilding the
  product or bypassing controls.

### Node 7 — Commercial scale

- **Outcome:** repeatable acquisition, delivery, retention, support, recovery,
  and portfolio learning under controlled authority.
- **Exit evidence:** independent assurance and every applicable production
  acceptance gate.

## Active-node execution card

### 1. Select

- Choose one authenticated, durable, tenant-owned state transition.
- Expected evidence: a record exists for the signed-in identity and cannot be
  read or changed by another identity.
- Maximum cost: no external action, credential, payment, or customer data.

### 2. Execute

- Add the minimum schema, server route, ownership query, UI, and test.
- Use server-injected ChatGPT identity; never accept identity from form data.
- Record an append-only audit event for every mutation.
- Stop when a missing platform guarantee would require fabricated security.

### 3. Evidence

- Record test result, deployed result, limitation, and next missing proof.
- Repeat when isolation holds; refine on implementation error; reroute to a
  separate backend if the host cannot meet the requirement; retire any feature
  that would misstate a payment or connection.

## Adversarial defense

Primary attacks are cross-tenant object access, spoofed identity headers outside
the platform boundary, fake subscription redirects, forged or replayed
webhooks, OAuth over-scoping, token leakage, connector prompt injection,
DALEOBANKS schema drift, confused-deputy requests, and operator pressure to
bypass holds. The earliest justified defenses are server-derived identity,
deny-by-default object ownership, append-only mutation records, no secrets in
the Site, explicit status vocabulary, and hard separation between `requested`,
`configured`, `verified`, and `active`.

## Exact next actions

1. **System Governor:** approve a launch price, billing provider, entity, terms,
   refund rule, support owner, and audience before Node 3.
2. **Platform implementation:** complete Node 1 without external authority.
3. **Security owner:** run two-identity isolation tests before inviting a beta
   user.
4. **DALEOBANKS and UAT owners:** approve sandbox endpoints, credential
   handling, delivery receipts, reconciliation, and incident ownership before
   adapter activation.
5. **LIVE PLAYER owner:** make the selected Library context readable and
   approve its classification, scope, expiry, and shadow evaluation before
   ingestion.
6. **Commercial owner:** obtain one costly or binding buyer action before
   presenting the product as commercially validated.

## Process quality gate

The backcast is internally complete across reality grounding, control-layer
diagnosis, assumptions, stakeholders, route comparison, falsification, stage
gates, operating loop, adversarial defense, and immediate action. External
completion remains blocked by missing public/customer access, commercial terms,
payment authority, provider credentials, DALEOBANKS runtime and reconciliation
evidence, readable and approved LIVE PLAYER context, paid demand, and
independent assurance.
