# Authenticated Constitutional Control API

## Purpose

`/api/v1/control` is the human-facing administration boundary for the durable
Venture Cell control plane. It does not accept an actor ID from request data.
Every mutation uses the subject from a verified, issuer/audience-bound JWT and
then intersects that subject with a separately configured authority set.

This is a single-process controlled-pilot reference. It does not turn SQLite,
JSONL, or shared-secret JWT signing into production-grade distributed control.

## Authority intersection

| Operation | Signed claim | Independent configuration | Effect direction |
| --- | --- | --- | --- |
| Read status, cells, grants | `admin`, `control:read` | Root or configured human subject | None |
| Create cell/grant; resume/terminate cell; revoke grant | `admin`, `control:root` | Exact root subject | Can configure/increase authority, subject to invariants |
| Pause cell; record exact-intent approval | `admin`, `control:approve` | Root or configured human subject | Pause reduces authority; approval is bounded to one fingerprint |
| Report incident | `control:incident` | Any cryptographically verified subject | Can only log, regress, or pause |

A role or permission in a signed token cannot add a subject to the independent
root/human set. Conversely, a configured subject still needs the exact signed
permission. Demo users have no control permissions by default.

## Endpoints

| Method and path | Required authority | Notes |
| --- | --- | --- |
| `GET /status` | Read | Returns integrity/continuity state, ledger head, counts, and active stage distribution. |
| `GET /cells`, `GET /cells/{id}` | Read | Returns charters and current status. |
| `POST /cells` | Root | Server assigns policy version, active status, and creation time; owner must be configured human. |
| `POST /cells/{id}/pause` | Human | Authority-reducing and easier than resume. |
| `POST /cells/{id}/resume` | Root | A terminated cell can never be resumed. |
| `POST /cells/{id}/terminate` | Root | Permanent terminal status. |
| `GET /grants`, `GET /grants/{id}` | Read | Optional list filter by cell. |
| `POST /grants` | Root | Initial stage is only `simulate` or `shadow`; expiry is capped. |
| `POST /grants/{id}/revoke` | Root | Irreversibly marks the lease inactive. |
| `POST /approvals` | Human | Server binds approver, policy version, approval time, and capped expiry. |
| `POST /incidents` | Incident reporter | Minor logs; major regresses; critical pauses the cell. |

Promotion is deliberately not exposed by this slice. The policy engine supports
one-stage promotion, but the external evidence-ingestion and independent review
queue must be durable before promotion becomes an HTTP operation.

## Required configuration

| Variable | Rule |
| --- | --- |
| `CONTROL_ROOT_AUTHORITY_ID` | Exact verified JWT subject; no default. |
| `CONTROL_HUMAN_AUTHORITY_IDS` | Comma-separated verified subjects; root is added automatically and at least two distinct humans must result. |
| `CONTROL_STATE_DB_PATH` | SQLite reference state. Explicit absolute path in production mode. |
| `CONTROL_EVIDENCE_LEDGER_PATH` | Separate JSONL ledger path. Explicit absolute path in production mode. |
| `CONTROL_POLICY_VERSION` | Defaults to `v1`; must match reconstructed state. |
| `CONTROL_MAX_GRANT_TTL_HOURS` | Defaults to 24; hard maximum 168. |
| `CONTROL_MAX_APPROVAL_TTL_MINUTES` | Defaults to 60; hard maximum 1,440. |

If authority configuration is missing, state is corrupt, the stored authority
map differs, or ledger reconstruction fails, control endpoints return a generic
503 and do not disclose integrity details to the caller. Production startup
also reconstructs this runtime and fails closed.

## Enforced invariants

- New root grants cannot start above A1 in either the API or policy engine.
- Executable authority requires recorded one-stage promotion.
- Request data cannot select approval or incident actor identity.
- Grant/approval TTLs cannot exceed deployment caps.
- Grant resource, geography, data, parameters, and budgets remain subsets of
  the charter and registered action policy.
- Pause requires a configured human; resume and termination require root.
- Cell/grant/approval changes, incidents, and authority changes append evidence
  and persist the complete policy snapshot.
- Restart reconstructs the same authorities and refuses mismatched identities.

## Production gaps

Before production canary, replace the shared-secret human verifier with a
workforce IdP and revocation/key rotation, move state to a replicated/fenced
store, transactionally retain administrative audit, independently anchor the
ledger, add workload identities and credential brokering, enforce egress, and
exercise downstream pause/revocation and reconciliation drills.
