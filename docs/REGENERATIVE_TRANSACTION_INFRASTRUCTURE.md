# Regenerative Transaction Infrastructure

Status: **proposed strategy doctrine; no runtime behavior or authority change**.
Business-evidence decision: **Validate**, not a claim of commercial validation.
Owner: Alfonso Lopez for intent and authorization; WMI maintainers for this document.
Source: founder request in the current conversation, 2026-09-17, to add and validate
this framework in WealthMachine. A stable conversation URL is unavailable.

## 1. Intended effect and boundary

GREG and Alfonso should discover and build businesses that make valuable recurring
transactions complete more reliably, improve legitimate participants' outcomes,
and earn durable economic value from that improvement. This is the preferred
discovery lens for the intended regenerative infrastructure ventures, not a rule
that every profitable venture must become a platform or settlement rail.

The founder's compressed skeleton is:

```text
Source of Truth (including explicit Eligibility)
    -> accepted Routing Authority
    -> Cashflow / Settlement
```

Keep four distinct analytical nodes even when presenting three factors:
**Proof / Truth + Eligibility -> Default Routing -> Cashflow / Settlement**.
Eligibility is a decision under a named actor's rules, not simply a fact in a
database. Evidence may be needed both before routing and after performance.
Disputes, corrections and reversals feed back into earlier states; the diagram is
not a mandatory one-way runtime or a claim that one business must own every node.

"Hegemony" means an accepted, reliable, hard-to-replace transaction function earned
through superior outcomes. It does not mean sovereignty over participants, forced
exclusivity, manufactured scarcity, arbitrary exclusion, or ownership of a market.
Proof, routing and settlement can be supplied by separate interoperable partners.

WMI remains a specialist assessor and proposer. Kernel owns institutional authority,
canonical contracts, evidence/event semantics and external consequences. Business
eligibility never grants a GREG worker permission to act. An accepted market
artifact is not automatically canonical institutional truth. See [AGENTS.md](../AGENTS.md).
This addition does not implement screening, change scores or wire schemas, create
agents or schedules, or authorize launch, outreach, custody, payments or deployment.

## 2. Four nodes, four separate proof obligations

| Node | Bounded question and artifact | Evidence required before claiming the position |
| --- | --- | --- |
| Proof / Truth | What happened, which evidence counts, and what status is current? Produce a versioned, attributable, time-bounded evidence package with correction and dispute paths. | A named independent buyer, verifier, payer or other consequential actor actually relies on the artifact for the stated purpose. Owning a database, signing a claim or passing an internal test is insufficient. |
| Eligibility | Who or what qualifies for this particular transaction under which rules? Produce a reasoned eligibility decision identifying policy owner, rule version, validity interval and appeal route. | The actor authorized to permit the transaction accepts the decision. True facts do not automatically establish eligibility; expired, revoked or out-of-scope proof must not qualify. |
| Default Routing | Where does valid work, demand, procurement or an exception go next? Produce a traceable assignment or escalation under an accepted operating agreement. | Actual workflow use, measured against all in-boundary opportunities, including bypasses and exceptions. Recommendation capability alone is not routing authority. Overrides, portability and fair access remain available. |
| Cashflow / Settlement | When is the obligation discharged, paid, approved or otherwise completed? Record accepted performance, responsible parties, applicable rail, reconciliation and residual obligations. | The relevant counterparty or settlement system confirms the consequence under identified rules. An invoice, payment instruction, API success or internal receipt alone is not settlement finality. |

Examples are hypotheses, not implemented capabilities: verified worker plus current
eligibility rules -> eligible opportunity; accepted supplier evidence -> procurement;
accepted completion evidence -> invoice approval or payment through an existing rail.
Each arrow needs its own permission, counterparty acceptance and outcome evidence.

**Truth is not cryptographic authenticity.** W3C's Verifiable Credentials Data Model
2.0 separates verification from evaluating claims under a verifier's business rules
and trust policy [S1]. This supports the distinction; it does not require WMI to
adopt that standard or imply that any WMI artifact has external acceptance.

**Finality is not a generic software status.** CPMI-IOSCO Principle 8 calls for a
defined point of final settlement and of irrevocability for financial market
infrastructures [S2]. Treat this as a design reference, not a determination that WMI
is an FMI or satisfies any regulation. A candidate must identify its actual legal,
contractual and rail-specific finality rules, reversals, disputes and liability.
Keep payment finality separate from warranties, refunds and other surviving duties.
Until those are evidenced, say pending, conditional or reconciled as appropriate;
do not promise absolute finality or assign liability by model assertion.

## 3. Discovery and the smallest viable wedge

Preserve the founder's search question:

> Where is a large recurring flow of money or human value being damaged because nobody reliably controls truth, eligibility, routing or settlement?

Interpret "controls" as responsibly establishes, verifies or coordinates the bounded
state with legitimate acceptance. A market may need better interoperability rather
than a new central authority. Search existing providers and workflows before building.

Use the existing [Income Streams Loop](../loops/IncomeStreamsLoop.md): find trapped
value -> name the authoritative external actor -> locate broken proof or eligibility
-> identify the routing decision -> identify the settlement/outcome event -> propose
the smallest buyer-backed wedge -> test acceptance -> expand only after evidence.

Default progression, not a timetable or guaranteed staircase:

| Proposed stage | Evidence needed to advance |
| --- | --- |
| Observe a broken transaction | Documented recurring failure, natural denominator, affected participants, payer and budget owner. |
| Fix one proof problem | A service or narrow tool beats the current workaround on a pre-agreed outcome; name who pays and why. |
| Become trusted for that proof | A consequential external actor uses the artifact for an actual decision, not just a demonstration or letter of interest. |
| Enter workflow and become a default | Repeat use, retained acceptance, measured routing share, funded reliability and participant choice. |
| Connect proof to settlement | Accepted proof changes payment timing, approval, loss or completion through authorized rails; reconciliation and dispute handling work. |
| Expand into adjacent transactions | New buyer acceptance, rights, economics and reliability are demonstrated independently in the next scope. |

Start manually or with an existing product when that is the cheapest decisive test.
Do not build a marketplace, payment processor, new ledger or three-layer platform
just to fit the diagram. A useful proof-only business may remain the best form.

## 4. Transaction dossier and advancement gate

For each candidate, attach this dossier to its existing review material; it is not
a new wire contract, runtime registry or source of permission. Use `unknown` rather
than filling gaps with model-generated certainty. For every material assertion,
record source, date, scope, owner, evidence tier, contradictory evidence and next test.
Distinguish verified fact, calculated illustration, working assumption, design choice,
and demonstrated external acceptance.

| Required dossier field | Minimum decision-relevant content |
| --- | --- |
| Transaction and failure | Actor, desired outcome, start/end, valid completion, frequency, unique flow, failure denominator and present workaround. |
| People and power | Buyer, budget owner, payer, beneficiary, mandate-capable acceptor, verifier, gatekeeper, veto holder and liability bearer. |
| Proof and eligibility | Broken state, accepted artifact, evidence origin, freshness/revocation, external acceptor, rule owner, eligibility decision and appeal. |
| Routing and consequence | Current route, proposed default, bypass/override, settlement event, partner/rail, legal basis, reversibility and remaining obligations. |
| Wedge and economics | Smallest paid offer, recurring value, willingness-to-pay evidence, cost to serve, sales/adoption burden, margins, cash timing and reserves. |
| Participant outcomes | Before/after benefit and cost by actor, access, time, errors, uncompensated work, privacy, rights, exclusions, appeal and restitution. |
| Reliability and defensibility | Failure limits, recovery, manual fallback, responsible operator, funded support, incumbent/free-bundle alternative and lawful reason to prefer us. |
| Learning and reuse | Permitted data purposes, retention, affected decisions, causal test, bias/gaming controls, reuse boundary and independent acceptance in each market. |
| Experiment and decision | Baseline, success threshold, budget, authorization, deadline, evidence owner, strongest dissent, kill criterion and next review. |

For this framework itself, **no specific market, paying buyer, accepted artifact,
measured routing share, actual settlement, realized revenue or participant gain has
been established by the supplied text**. These are unknown, not zero-valued market
measurements and not implicitly passed gates.

An unknown decisive fact supports **Validate** and a bounded test, never automatic
advancement. Evidence that there is no buyer, no useful external consequence, no
lawful permission path, irreducible harm or unfundable reliability requires
reconfiguration, parking or termination as appropriate. Do not average fatal failures
away with a high total score. A stage recommendation is never execution authority.

## 5. Economics: throughput is not revenue or profit

The founder's arithmetic is correct as a conditional illustration:

```text
$10,000,000,000/year x 0.5% = $50,000,000/year
$10,000,000,000/year x 1.0% = $100,000,000/year
```

These are not estimates of an identified market, demand, reachable revenue or profit.
They assume the full $10B is billable at the stated rate. At 10% adoption and a 0.5%
fee on that adopted flow, the same illustration yields $5M/year before costs.

A more explicit planning identity is:

```text
Annual fee capture = unique in-scope annual transaction value
                   x adopted share
                   x billable share of adopted flow
                   x contracted fee rate
                   x retained share after partner fee splits
```

Define each denominator and avoid multiplying overlapping adoption factors or
counting the same transaction once for proof, again for routing and again for
settlement. Flat fees or subscriptions need their own unit-based model. Accounting
revenue presentation depends on the actual arrangement; this is fee-capture math.
Then deduct processing, verification, fraud/loss, support, compliance, reliability,
customer acquisition and operating costs; model working capital and downside cases.

A small percentage of gross flow does not prove fair pricing or regenerative value.
Compare total participant outcomes with the baseline, including fees, new burdens,
risk shifts and rights. Volume handled is not the value created. Customer, escrow,
restricted or refundable funds are never assumed to be available growth capital.

## 6. Learning, participant strength and capital compounding

Preserve the founder's intended loop, with evidence gates on every arrow:

```text
SOURCE OF TRUTH -> ROUTING AUTHORITY -> SETTLEMENT FINALITY
-> PROPRIETARY LEARNING -> BETTER PARTICIPANTS -> MORE TRUSTED TRANSACTIONS
-> MORE CAPITAL -> NEXT MARKET
```

The first node includes explicit Eligibility; "finality" remains conditional on
Section 2. This is an aspiration to test, not an automatic causal law.

Learning must come from legitimately obtained transaction evidence and improve an
accepted decision, not merely accumulate records. Test a specific intervention
against a baseline or justified comparison; record sample limits and uncertainty.
Before claiming a mature intelligence engine, demonstrate improvement in at least
three consequential decisions, such as eligibility, routing and dispute resolution.
Model output, correlation, data volume and ordinary scale economies are not proof
of causality, a proprietary advantage or a network effect.

Measure operational completion, capital/cash timing, institutional acceptance and
participant welfare as distinct loops, with delays, failure modes and saturation.
Use clean-completion rate, proof-acceptance rate, payment/approval time, dispute and
wrongful-exclusion rates, participant net benefit and contribution margin. Define
coverage against all in-boundary transactions, including failures and bypasses;
never manufacture non-bypassability by blocking legitimate exit or alternative proof.

Assess Commercial, Strategic, Regenerative, Institutional and Capital integrity
separately. No economic gain excuses participant harm or weakens governance. Do not
claim success in any dimension without evidence appropriate to that dimension.
Capital available for a next market is surplus after obligations, losses, reserves,
reliability, participant protection and authorized reinvestment, not gross throughput.

Across Venture Cells, identify reusable proof, routing and settlement capabilities.
Extract a shared implementation only after repeated need and comparative evidence
justify it; reuse existing Kernel contracts rather than creating a second control
plane. Shared code does not imply shared customer data, transferable market trust,
pooled money or cross-market authority. Each cell keeps its data rights, liability,
acceptance rules and permission boundaries. Review conflicts when a cell both
verifies claims and benefits from directing the resulting transactions.

## 7. Rights and failure conditions

Require transparent eligibility, appeal, correction, auditability, interoperability,
portability, data minimization, purpose limits, security, manual fallback and fair
access. Do not optimize fees by delaying payments, routing to a worse affiliated
provider, hiding disputes, exploiting participants or making records hostage to exit.
No undisclosed data reuse or claim of regulatory recognition is permitted.

Stop advancement on forged or stale proof, unaccepted eligibility, unauthorized
routing, duplicate or uncertain effects, unreconciled settlement, material privacy
harm, wrongful exclusion, or losses beyond funded limits. Define recovery, notification,
restitution and responsible human review before any authorized consequential pilot.
An outage of a proof service must not silently turn into permanent participant denial.

## 8. Founder-intent lineage and integration decision

Local reference IDs below do not allocate or override Kernel intent IDs. Shared
source: the 2026-09-17 founder request; Sections 1 and 6 preserve its
meaning, and Section 3 quotes its search question. No claim of cryptographic founder authentication is made.

| Local intent | Statement and lifecycle | Scope, evidence and review |
| --- | --- | --- |
| WMI-TX-20260917-1 | Add the proof/eligibility -> routing -> settlement discovery framework; `active` request, `active_requirement` for this bounded documentation task. | WMI strategy documentation only. This document and its two entry links are the implementation; review the draft before adoption. |
| WMI-TX-20260917-2 | Build regenerative infrastructure businesses through a small proof wedge; `needs_evidence`, `aspiration` for commercial outcomes. | All four nodes, participant welfare and economics remain externally unproven here. Review after a separately authorized acceptance test. |
| WMI-TX-20260917-3 | Reuse primitives and compound into adjacent markets; `deferred`, `aspiration`. | No shared runtime, data pooling or capital allocation introduced. Revisit after repeated independently accepted outcomes and rights review. |

Owner for intent and unresolved scope: Alfonso. Proposed operational review owner:
WMI maintainer. Dependencies: existing Income Streams Loop and Kernel boundaries.
Conflict disposition: literal ownership/finality/inevitable compounding is not
adopted; the desired effect is preserved as evidence-gated capability. No prior
intent is superseded. Superseded-by: none. Runtime implementation references: none.

### Two strengthening passes

**Pass 1 - make the thesis falsifiable.** The four nodes expose where a recurring
transaction breaks; turn that advantage into one named acceptor and a measurable
consequence. D1: data possession could masquerade as truth -> require external
acceptance and explicit eligibility. D2: full-stack ambition could cause premature
capital/control -> start with one wedge and existing rails. D3: fee arithmetic could
masquerade as business proof -> separate adoption, billability, costs and welfare.
These advantages reverse if acceptance is nominal, integrations dominate costs or
measurement shifts burdens onto participants.

Alternatives: the current generic loop is simple but leaves these claims implicit;
do nothing adds no maintenance but loses the requested lens. A one-paragraph slogan
is cheaper but omits decisive failure gates. The selected linked doctrine is the
smallest sufficient review mechanism. A competing executable scorer could enforce
fields but creates false precision and contract/maintenance work before a validated
dossier exists; revive only after human-reviewed cases show repeatable requirements.
An existing service/provider plus manual acceptance test is the preferred reversible
market experiment, not a reason to invent infrastructure now.

**Pass 2 - attack the strengthened proposal.** N1: a checklist can become ceremony
or be gamed -> keep one dossier in existing review material; no new registry, score
or runtime. N2: accepted defaults could become coercive exclusion -> preserve choice,
appeal and interoperability. N3: shared learning could overreach -> require purpose
rights and fresh acceptance in each market. D1 remains `experiment` until external
acceptance; D2 is `resolved` for this change by documentation-only scope; D3 remains
`experiment` until reconciled unit economics and participant outcomes. WMI maintainer
owns these dispositions; review triggers are the first candidate dossier and each
proposed stage expansion. Residual risks are buyer refusal, costly adoption,
measurement bias and harmful concentration; mitigate through the bounded comparison,
rights controls and stop conditions, not through claims that the risks are solved.

Five-role review below is one assistant's analysis, **not independent review**:

| Perspective | Position, concern and recommendation |
| --- | --- |
| Founder-Intent Steward / Constitutional Reviewer | Preserve the full economic destination; no market metaphor grants authority. Retain the bounded proposal under AGENTS.md and Kernel INTENT-0030. |
| Systems Architect / Builder | Reuse the existing loop and contracts. Retain one linked doctrine, not another runtime or shared schema. |
| Adversarial Reviewer | Proof acceptance may not create willingness to pay or defensibility. Retain dissent; do not promote a business without an observed consequential acceptance and credible paid-value test. |
| Operator and Maintainer | Avoid a new evaluator or mandatory platform build. Retain a reversible documentation change; revisit only when actual review cases expose a missing function. |
| Evidence and Welfare Guardian / Beneficiary Representative | Low fees and good intentions do not establish welfare. Retain only with before/after burdens, rights and participant-outcome evidence before expansion. |

Material dissent remains with the adversarial and welfare perspectives. The WMI
maintainer owns follow-up at the first pilot review; actual buyer reliance, a
credible paid offer and measured non-harm are the evidence thresholds, not model
agreement. Institutional decision: **RETAIN this bounded proposal for draft review**;
it does not approve a venture or authorize the experiment described below.

Migration: add this document and links from README and the existing loop; no runtime,
state, dependency, schema or cross-repository migration. Rollback: leave the PR
unmerged, or use a normal revert if later adopted; no history rewrite. Regress the
document if it starts creating a parallel policy/runtime, compels harmful lock-in,
or is repeatedly used to label unsupported market claims as validated.

## 9. Evidence ledger and next decisive test

Inspected WMI baseline: `ec82b8027d987c865dc123215afb53d20916908f`; AGENTS.md,
CLAUDE.md, README.md, the integration-boundary portions of Instructions.md,
ontology/ontology-schema.yaml and loops/IncomeStreamsLoop.md. The inspected docs
folder held the SR-001 handoff; this is a bounded addition, not a whole-repository
audit. A search for open PRs containing "hegemony" returned none; that is not proof
that all branches or differently named proposals are free of overlap.

Kernel boundary reference: `04b1b7e3bce5fd8ea6fbaf978719249cae8ef90a`; agent entry,
founder-effect compiler, INTENT-0030, intent ledger, collaboration protocol,
canonical execution order and Final Build Order lines 1-220 inspected.
These are source-inspection evidence, not tests of runtime behavior.

- [S1: W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/), 15 May 2025; verification, trust model and privacy distinctions; reviewed 2026-09-17. Primary-source precedent, not market acceptance.
- [S2: CPMI-IOSCO Principles for Financial Market Infrastructures, Principle 8](https://www.bis.org/committees/cpmi/pfmi/overview), reviewed 2026-09-17. Primary-source finality reference with the scope limitation in Section 2.
- Fee illustrations in Section 5: calculated from explicitly hypothetical inputs. No market-size or revenue forecast is supplied.
- Negative evidence: no selected transaction, external acceptor, customer result or commercial outcome was supplied. No automated-screening or settlement capability is implemented by this patch.

**Decision: Validate.** Next external action, only after separate authorization:
select one bounded transaction and ask one named, non-affiliated consequential
acceptor to use a minimum proof artifact for a real decision under agreed criteria.
External number to change: documented consequential proof acceptances from an
unmeasured baseline to at least one observed acceptance; separately compare one
pre-agreed completion, delay, error or burden metric with the current workaround.
Required evidence: dated acceptance tied to the actual decision, baseline and result,
participant effects, costs, dissent and the buyer's paid-value response. One accepted
case tests the mechanism, not repeat demand, market coverage or investment readiness.
Proposed deadline: 30 days after the pilot is authorized, with a hard 90-day maximum
for the initial control-point test. Terminate or redesign the candidate on explicit
acceptor rejection with no viable alternate, irreducible participant harm, no lawful
path, or failure to demonstrate consequential acceptance by the agreed deadline.
No outreach, spend, pilot or recurring task is authorized by this document.
