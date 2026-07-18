# Progressive Autonomy Inside Venture Cells

## Governing rule

Autonomy is a **revocable, expiring capability lease**. It applies to one agent,
one action type, a resource prefix, a context fingerprint, parameter constraints,
data and geography scopes, and a budget envelope.

A displayed “cell level” is informational only. It must show the distribution
of active capability stages and the highest active risk tier; it must never be
used as an authorization token.

## Capability stages

| Stage | Name | Side effects | Evidence to advance | Automatic response |
| ---: | --- | --- | --- | --- |
| A0 | Simulate | None. Analyze approved data and generate hypothetical intents. | At least 10 representative evaluations, complete logs, and failure upper bound within configured policy. | Any attempted bypass is denied and logged. |
| A1 | Shadow | None. Evaluate real intents against policy and compare with approved outcomes. | At least 29 representative zero-critical-failure trials over 7 days, full audit coverage, one rollback drill, and clean critical red-team findings. | Context change keeps or returns the capability to shadow. |
| A2 | Supervised canary | Reversible internal actions for a narrow cohort under an explicit grant. | At least 99 representative trials over 14 days, failure upper bound at or below 3%, two rollback drills, and no policy violations or critical findings. | Major incident regresses one stage; critical incident pauses the cell. |
| A3 | Bounded | Approved internal and bounded external workflows within aggregate caps. Material actions still need exact-intent dual approval. | At least 299 representative trials over 30 days, failure upper bound at or below 1%, three rollback drills, full auditability, and clean critical red-team findings. | Drift, degraded controls, incidents, expiry, or budget breach deny/regress. |
| A4 | Scaled bounded | Higher throughput in the same proven action/resource/context envelope. | No further autonomous stage. A broader context is a new capability starting in shadow. | Same limits remain; there is no “unlimited” level. |

The counts above are defaults, not universal safety guarantees. Each action class
must also use a representative test design and severity-weighted failure
definition. Correlated trials, repeated easy cases, or missing audit data do not
count as independent assurance.

The implementation enforces the starting boundary in the policy engine: a new
root grant can be issued only at A0 or A1. A request for A2–A4 is rejected even
from a configured root, so no HTTP route, script, or alternate trusted caller
can use grant creation to skip the evidence ladder. Each later transition uses
the one-stage promotion method and is recorded in the Evidence Ledger.

## Two independent evidence lanes

| Lane | Question | Strong evidence | What it can unlock |
| --- | --- | --- | --- |
| Venture viability | Should this business receive more capital and attention? | Payments, retained usage, contribution margin, support burden, signed pilots. | Capital, staffing, experiment budget, or continuation. |
| Control assurance | Can this exact capability execute inside its envelope reliably? | Representative execution trials, upper failure bound, policy violations, audit completeness, rollback drills, red-team results, incident history. | A one-stage capability promotion. |

Revenue never cancels a policy violation. Clean execution never proves product
market fit. Promotion requires the assurance lane; venture scaling requires the
viability lane.

## Statistical evidence rule

For zero observed failures in \(n\) trials, the exact one-sided 95% upper bound
on the failure probability is:

\[
p_{upper} = 1 - 0.05^{1/n}
\]

Wolfram Language was used to verify the implemented values:

| Zero-failure trials | 95% upper failure bound |
| ---: | ---: |
| 5 | 45.07% |
| 10 | 25.89% |
| 29 | 9.82% |
| 99 | 2.98% |
| 299 | 0.997% |
| 2,995 | 0.100% |

This is why “5 successful actions” or “10 good drafts” cannot justify broad
autonomy. Even 10 zero-failure observations remain statistically compatible
with a failure rate above 25% at 95% confidence.

When failures are observed, the implementation calculates the exact one-sided
Clopper–Pearson upper bound. Promotion criteria use the upper bound, not the raw
observed rate.

## Risk tiers

Action risk is registered by trusted policy administrators. Agents cannot lower
their own classification.

| Tier | Examples | Default treatment |
| ---: | --- | --- |
| R0 Observe | Read approved data, calculate, draft. | Grant-scoped read access; no side effect. |
| R1 Reversible internal | Update a low-risk internal record, route a task. | A2+ within explicit resource and parameter scope. |
| R2 Bounded external | Pre-approved message, bounded experiment, capped spend. | A3+ with recipients, content, resource, data, geography, and aggregate budget limits. |
| R3 Material | Fund transfer, material/custom agreement, consequential public claim. | Exact-intent approval by at least two distinct registered humans; no delegation. |
| R4 Constitutional | Change policy, charter, monitoring, kill conditions, root identities, or evidence rules. | Denied to agents at every stage. |

## Permanently non-delegable authority

Agents cannot autonomously:

- promote their own grants or weaken promotion criteria;
- change charters, missions, root identities, monitoring, audit, or kill controls;
- create broader, longer-lived, or deeper child authority;
- access raw broad credentials or bypass the execution gateway;
- enter a new geography, regulated activity, sensitive-data class, or customer
  segment without a new charter decision and shadow validation;
- accept material liability, debt, custom legal terms, or material transfers
  without the configured human/dual control;
- issue public crisis, legal, safety, or regulated-performance communications;
  or
- resume a terminated cell.

Routine, counsel-approved, low-value agreements may eventually be represented
as tightly parameterized R2 templates. Material or non-standard agreements
remain R3. This is more precise than permanently routing every clickwrap or
standard purchase through a human while preserving human control over legal
exposure.

## Promotion and regression rules

Promotion requires all of the following:

1. a configured criterion for the action and target stage;
2. exactly one stage of movement;
3. evidence from the same model/prompt/tool/data/policy context;
4. an intact Evidence Ledger chain;
5. objective criteria passing; and
6. an independent root-human approver and review identifier.

Human API operations use the intersection of two independent sources: signed
JWT claims and a separately configured authority allowlist. A token cannot
self-declare root authority, and request payloads cannot choose the actor of an
approval or incident.

Regression is deliberately easier:

- expired grant: deny;
- changed context fingerprint: shadow and revalidate;
- budget or scope breach: deny;
- major incident: regress the affected grant;
- critical incident: pause the cell;
- terminated cell: deny permanently.

Commercial metric degradation should reduce capital or pause venture activity.
It should not silently alter unrelated control-assurance records.
