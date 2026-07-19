# Venture Cell Charter Template

Copy this document for each cell. Replace every bracketed value. Missing or
ambiguous authority defaults to denied.

## 1. Identity and mission

| Field | Value |
| --- | --- |
| Cell ID | `[stable-id]` |
| Charter version | `[semver or date]` |
| Control-policy version | `[policy-version]` |
| Root human owner | `[verified identity]` |
| Independent reviewer(s) | `[verified identities]` |
| Mission | `[one narrow, falsifiable outcome]` |
| Explicitly out of scope | `[segments, products, actions, or claims]` |
| Start date | `[UTC timestamp]` |
| Review / expiry date | `[UTC timestamp]` |

## 2. Venture success contract

Commercial evidence controls continuation and capital; it does not promote
agent authority.

| Item | Definition |
| --- | --- |
| Customer problem | `[specific costly/urgent workflow]` |
| Buyer / user / beneficiary | `[identify each separately]` |
| Primary outcome metric | `[externally observable metric]` |
| Baseline and target | `[value -> gate]` |
| Capital cap before new evidence | `[$ amount]` |
| Continue threshold | `[objective condition]` |
| Revise threshold | `[objective condition]` |
| Pause threshold | `[objective condition]` |
| Kill threshold | `[objective condition]` |

## 3. Cell boundary

| Scope | Allowed | Prohibited / requires re-charter |
| --- | --- | --- |
| Customer segments | `[list]` | `[list]` |
| Geographies | `[list]` | All others |
| Data classes | `[public/internal/etc.]` | All others, especially regulated data unless signed off |
| Systems / tenants | `[resource prefixes]` | All others |
| External channels | `[list]` | All others |
| Legal / regulatory regimes | `[approved analysis]` | Novel or unreviewed regimes |

## 4. Budget and exposure envelope

| Limit | Cap |
| --- | ---: |
| Per action | `[$]` |
| Per capability per day | `[$]` |
| Cell per day | `[$]` |
| Cell lifetime | `[$]` |
| Maximum customer cohort | `[# or %]` |
| Maximum messages per day | `[#]` |
| Maximum reversible data changes | `[# / resource scope]` |
| Maximum unresolved liability | `[$ or none]` |

Splitting actions may not evade an aggregate cap. Reaching a cap denies further
execution; only the root-human charter workflow can increase it.

## 5. Capability register

Create one row per action type and agent. The stage is not inherited by other
rows.

| Grant ID | Agent identity | Action | Risk | Stage | Resources | Parameter constraints | Context fingerprint | Expiry | Delegation depth |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | ---: |
| `[id]` | `[id]` | `[registered action]` | `[R0-R3]` | `[A0-A4]` | `[prefixes]` | `[allowed values/templates]` | `[digest]` | `[UTC]` | `[0-2]` |

For each capability, attach:

- entry condition;
- representative trial definition;
- failure definition and severity;
- promotion criteria identifier;
- rollback procedure and maximum recovery time;
- monitoring source and owner; and
- current assurance-evidence reference.

## 6. Human and dual-control decisions

Name the exact actions requiring one or more humans. At minimum include:

- material/custom contracts or legal commitments;
- material transfers, debt, or liability;
- novel public performance or safety claims;
- new geography, segment, regulated activity, or sensitive-data scope;
- production context changes that invalidate assurance;
- authority promotion and budget increase;
- charter, policy, monitoring, identity, and kill-control changes;
- public crisis or legal response; and
- resuming a critically paused cell.

| Action class | Required approvers | SLA | Expiry | Backup path |
| --- | ---: | --- | --- | --- |
| `[class]` | `[# distinct verified humans]` | `[time]` | `[time]` | `[safe default: deny/pause]` |

## 7. Kill conditions and incident response

Automatic pause conditions:

- critical policy bypass or suspected credential compromise;
- Evidence Ledger integrity failure;
- material action without valid approval;
- access outside charter geography/data/resource scope;
- aggregate budget counter failure;
- inability to observe or stop consequential execution; or
- `[cell-specific conditions]`.

| Severity | Immediate response | Human owner | Recovery evidence |
| --- | --- | --- | --- |
| Minor | Log, investigate, remain bounded if safe. | `[owner]` | `[evidence]` |
| Major | Regress affected capability; reconcile side effects. | `[owner]` | `[evidence + rollback test]` |
| Critical | Pause cell and revoke downstream access. | `[root owner]` | `[independent review + reauthorization]` |

## 8. Evidence and audit

| Evidence source | System of record | Cadence | Completeness target | Retention |
| --- | --- | --- | ---: | --- |
| Intents and policy decisions | `[ledger]` | Per action | `100%` | `[period]` |
| Execution receipts | `[ledger / downstream]` | Per action | `100%` | `[period]` |
| Commercial outcomes | `[billing/product/CRM]` | `[cadence]` | `[target]` | `[period]` |
| Incidents and support load | `[system]` | `[cadence]` | `[target]` | `[period]` |
| Red-team results | `[system]` | Before promotion / release | `100% critical cases` | `[period]` |

## 9. Sign-off

| Decision | Identity | Date | Evidence / signature reference |
| --- | --- | --- | --- |
| Charter approved | `[root human]` | `[UTC]` | `[reference]` |
| Compliance scope approved, if applicable | `[authority]` | `[UTC]` | `[reference]` |
| Initial capability grants approved | `[root human]` | `[UTC]` | `[reference]` |
| Independent review completed | `[reviewer]` | `[UTC]` | `[reference]` |
