# Implementation Instructions

## Integration Recovery — WMI authentication/startup (2026-09-07)

Binding scope: Alfonso's September 5 audit follow-up, repeated September 7 in
the current chat. Manual development direction, not runtime authentication.
One bottleneck, one repair branch, draft only; no merge, deployment, credentials,
founder enrollment, external effects, or authority expansion. The existing audit's
two passes govern; this implementation is not a third strengthening pass.

Inspection ledger (source inspection, not execution proof):

| Source | Revision | Disposition |
| --- | --- | --- |
| WMI main | ec84b6a2eec4efbc07bed7f167da81f5e25d890c | Baseline: root Docker CMD misses bridge; root demo fallback; auth anonymous admin; root JWT stub |
| WMI #23 | e76c041762b913187754b76b8c32e539b9bd2da7 | Extract jose verification, fixed algorithm and signed claim normalization; do not retain demo issuer or development defaults |
| WMI #24 | 57e9f8d8e24e0a8e070334b56ebf5dee2c9dd2b1 | Benchmark identity/authority separation; defer control API, no new organ authority engine |
| WMI #31 | 45e3d02e1e1fd71433a810b390e337c39097cef7 | Extract missing-key refusal; preserve full branch, do not import unrelated changes |
| WMI #32 | efbf524113c3c1805264459f64442e77fe1dd279 | Extract explicit non-isolated HMAC identity labeling; no unsigned HTTP compatibility mode |
| Kernel ownership/rationalization records | PR #94 tree, 5e2f221b1911309db10de26246065553c1bdcbfc | Read only; Kernel remains shared-contract and consequence owner |
| September 5 seven-repository audit | founder-reported 816 entries / 232 branches / 109 PRs | Not independently re-inventoried here; full audit artifact not located in inspected WMI tree |

Files inspected: root and Enhanced Dockerfiles, main.py, src/api/main.py,
src/api/auth.py, jwt.py, bridge routes/transport/intake, route dependencies,
database startup, conftest.py, HTTP tests, contract parity tests, CI, README,
Instructions, DEPLOYMENT_SUMMARY, Enhanced Keycloak implementation and entrypoint.
Non-executing inventory and exact duplicate scan completed before edits.

Canonical ownership within this repair:

| Concept | Owner/source | Preserved alternative |
| --- | --- | --- |
| ASGI application | WMI src/api/main.py | Prior root app retained as historical text; Enhanced generation remains experimental and excluded from root image |
| JWT verification | WMI src/api/auth.py, adapted from #23 | Old defaults and JWT stub preserved in Git/history, never a fallback |
| main:app compatibility | WMI root main.py re-exports src.api.main:app | Supports existing Python/Uvicorn callers; expires when all startup consumers use canonical path; remove only after parity tests and consumer migration |
| Transport semantics | Kernel versioned bridge interface; WMI src/services/bridge_security.py transitional consumer | Existing HMAC wire v1.0/v1.1 compatibility, shared-secret identity NOT isolated; expiry: canonical durable adapter available; removal: consumer parity and restart gate pass; failure: refuse, never unsigned downgrade |
| Authority/external effects | Kernel / Consequence Gate only | No WMI control API from #24 adopted |

The prior checklist below is historical, not current readiness evidence. In
particular src/app/main.py does not exist. This repair uses the existing bridge
application, not the previously proposed application generation.

### Mechanisms reused, not a new architecture

Known precedent: [JWT Best Current Practices, RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html),
especially algorithm verification and audience validation; local implementation
precedent WMI #23. No novel cryptography or superiority claim.

1. **Claim-bound admission**: purpose/primitive = verify a signed, expiring,
   recipient-bound principal before routing. State/memory = configured trust
   parameters, no demo user table; transition = credential to principal or refusal.
   Actors = caller, WMI verifier, operator; authority = externally configured trust,
   never a grant issuer. Visible = normalized claims; hidden = signing key.
   Resources = bounded token verification; incentives = invalid input cannot obtain
   useful work by withholding configuration. Feedback/threshold = 401 invalid,
   503 unavailable, startup error before DB creation. Selection = fixed HS256,
   explicit issuer/audience, no algorithm negotiation. Trust boundary = request
   admission; proof = jose verification exercised through real dependencies.
   Failure/recovery = refuse then retry only after configuration repair.
   Consequence = internal proposal route, no external effect.
   Invariant = identity evidence never manufactures Kernel authority.
   Three mutations from #23: remove local issuance/demo password path; require
   configuration in **every** environment; revalidate configuration at each request
   rather than retaining permissive import-time defaults. Additional mutation:
   both shared-key JWT and signed-body checks guard bridge POST, not a static token.
2. **Startup control-path binding**: purpose/primitive = route packaged startup to
   one already-existing ASGI owner. State/memory = Docker COPY/CMD plus historical
   snapshots; transition = process startup to validated app or terminal error.
   Actors = packager/operator/test harness; authority = no new permissions.
   Information = published entrypoint and exact source set; resources = one API
   process, no extra metrics listener. Incentive = a green isolated auth unit test
   cannot substitute for exercising the packaged route. Feedback/threshold =
   subprocess exit or protected HTTP acceptance. Selection = canonical bridge
   rather than demo/root or Enhanced generation. Trust boundary = import and
   package composition; proof = fresh-process HTTP with no dependency overrides.
   Failure/recovery = dependency/configuration errors propagate, no demo fallback;
   preserve comparison sources and return to unactivated baseline if rejected.
   Consequence = no deployment. Invariant = only one active application owner.
   Three mutations: replace root app with canonical re-export; package by positive
   source allowlist excluding fixture/history/Enhanced; test exact CMD and copied
   source outside the repository with invalid **and** valid synthetic traffic.

HMAC remains a temporary compatibility mechanism, not isolated workload identity.
PRs #31/#32 refusal is strengthened here by disallowing unsigned HTTP entirely.
No blockchain, tokens, authority engine, identity registry, credentials, model
framework, or new runtime was introduced.

### Bounded eight-side check (not another strengthening pass)

| Side | Executable or retained consequence | Super-node |
| --- | --- | --- |
| 1 Reality/failure | Old suite green; new negative controls red before repair | Proof / Truth |
| 2 Participants | Operator configures trust, caller cannot mint it | Eligibility |
| 3 Permission | Verified claims and required body signature, no demos | Eligibility |
| 4 Default routing | Docker and root shim route to src.api.main | Default Routing |
| 5 Proof | Retained failing logs and fresh-process HTTP tests | Proof / Truth |
| 6 Resources | Refuse misconfigured startup before DB creation; one metrics route | Resource / Settlement |
| 7 Reuse | Existing PR mechanisms extracted, consumers must migrate explicitly | Default Routing |
| 8 Continuity | Historical sources, recovery manifest, unmerged rollback | Proof / Truth |

Implementation review perspectives (one assistant's checks, **not independent
human review**, not new formal passes): intent steward preserves full UNIIMENTE
destination; architect selects the existing bridge; adversarial review preserves
the fact that symmetric keys do not isolate identities; maintainer requires exact
startup tests and records Docker's absence; evidence guardian refuses production,
authentication-of-Alfonso, or external-outcome claims. Dissent remains: this is not
a sufficient shared identity/replay foundation, and stricter JWT admission breaks
old DALEOBANKS clients until their compatibility gate passes. Do not activate it.

### Evidence and contributor handoff

Evidence home: `tests/evidence/wmi-auth-recovery/`. Commands use Python 3.12 and
the isolated scratch dependency directory; CI's Python 3.11 remains separately
unverified until its actual run. Reproducible commands once dependencies exist:

```
python -m pytest tests/test_auth_boundary.py tests/test_packaged_startup.py tests/test_signed_bridge.py tests/test_opportunity_intake.py -q --tb=short
python -m pytest -q --tb=short
ruff check src/api/auth.py src/api/main.py src/api/routes/opportunities.py src/services/bridge_security.py main.py tests/test_auth_boundary.py tests/test_packaged_startup.py tests/fixtures/auth.py
git diff --check
```

Preserved progression: baseline 83 passed; first negative controls 30 failed / 2
passed; repaired auth controls 32 passed; old HTTP fixtures then 10 failed / 105
passed because they supplied no JWT or expected unsigned admission. Fixtures were
migrated to real synthetic signatures, not dependency overrides. Next focused run
62 passed / 1 failed (readiness used 127.0.0.1, blocked by existing production
TrustedHost policy); changing the test to localhost preserved the policy and
yielded 5 packaged-startup passes. Interim broader run: 120 passed. Final results
are in `final-results.md` beside raw logs. Earlier negative results are not erased.
An initial dependency-install process became unavailable after session interruption;
the later install succeeded. Two rejected patch applications made no edits; lint
initially reported 33 findings, 29 mechanically fixed, 4 then explicitly fixed.

Evidence tiers: source inspection for ownership/bypass findings; deterministic
fixtures/unit tests for claim refusal; local sandbox subprocess HTTP for startup
composition. **Docker executable absent**: no container build or image execution
claimed. No actual founder credentials, enrollment, authenticated mission,
Cathedral closure, economic result, independent review, or production security
claim. CMC remains 0. Kernel #94's 78/207/1440 passes and three reproduced baseline
failures remain prior Kernel evidence, not this WMI suite's results; PR #94 is
untouched. No new global institutional metric has been earned.

Preservation: `historical/root-main-ec84b6a2.py.txt` retains the root implementation
with only a final newline added; original exact Git blob is
`40dfb30ab25dcd8fd35cdc8b3b800cff6c1b6831`. JWT stub fixture retains exact blob
`a638a995b0a93f7f84444a282fdb02eee935cf4e`. Bytecode manifest preserves all 56
original Git object references; no Git history was rewritten. Enhanced source,
specialist roster, venture logic, schemas, migrations, Kernel, DALEOBANKS,
PumpStation and RailScout implementations are unchanged. Generated bytecode removal
shares this bounded PR because the founder explicitly required packaged hygiene.

Rollback: leave this branch draft/unmerged; main remains ec84b6a2. Recover original
files by their recorded parent/blob references, in a review branch, not via force
push or deletion of evidence. Never restore permissive authentication into an
activated service. Kill this candidate if any known bypass succeeds, a fixture
enters the image, required auth dependency fails open, or an organ begins issuing
institutional authority. PR #23/#31/#32 remain extract-specific-mechanisms sources;
#24 remains a benchmark with control administration deferred; no PR was closed.

Next bottleneck after this local admission/startup gate: canonical cross-repository
transport and integrity semantics, beginning with missing-key parity and retained
negative controls. Required sources remain Kernel #71/#87/#85/#93, DALEOBANKS
#71/#74, WMI #31/#32. Process-local nonce/idempotency caches, response-byte signing,
schema completeness, translation identity, per-workload isolation, grant validity,
ledger genesis/constitution binding and durable replay remain unearned. Do not
advance runtime composition until those gates pass. No merge/deployment ruling is
requested merely to continue authorized draft development.

This document tracks the work required to bring the **WealthMachine** project to full‑stack, production‑grade quality.  It captures the acceptance criteria and the execution plan defined in the work order.  As the implementation progresses each item in the checklist below should be checked off.  If a blocking issue arises, document it in the `Blockers` section.

## Acceptance Checklist

* [ ] **CI passes** – All continuous integration checks (lint, type checking, tests, security scans and Docker build) must succeed without errors.
* [x] **Single entrypoint and DB path** – The application exposes a single ASGI app (`src/app/main.py`) and uses a single database connection and migration path (`alembic/`).  There must be no competing modules or duplicated migration directories.
* [ ] **Comprehensive tests and coverage** – Unit, integration, end‑to‑end and load tests must exist for all code paths affected by this work.  New functionality requires accompanying tests and the overall coverage of core services should meet or exceed the target (≥ 80 %).
* [x] **Updated onboarding docs** – The README and supporting docs (e.g. `ARCHITECTURE.md`, `RUNBOOKS.md`) must be updated to ensure a new engineer can understand, set up and run the system in under fifteen minutes (MTTC ≤ 30 min).
* [x] **Secret hygiene** – No secrets or credentials are committed to the repository.  All configurable values should be loaded from environment variables with examples provided in `.env.example`.
* [x] **Observability preserved** – Liveness/readiness probes, structured JSON logging, metrics and traces remain functional.  Any new endpoints include appropriate logging and metrics hooks.

## Execution Plan

1. **Repository normalisation** – Verify that there is a single ASGI entrypoint (`src/app/main.py`) and that database access is encapsulated in a single module (`src/app/db`) with migrations under `alembic/`.  Remove or merge any duplicate code paths.  Ensure Alembic configuration loads the correct metadata.
2. **Tooling and build system** – Confirm that development tools such as Ruff, Black, MyPy and pytest are configured via `pyproject.toml` and `Makefile`.  Pin dependency versions to avoid drift.
3. **Runtime and deployment** – Ensure Dockerfile and `docker-compose.yml` build a working container and expose `/healthz`, `/readyz` and `/livez` endpoints.  Provide `.env.example` with all required variables.  Confirm the ASGI app uses environment variables instead of hard‑coded values.
4. **Observability** – Validate that JSON logging via `structlog` is configured and that Prometheus metrics are exposed via middleware.  Add request IDs or tracing context if needed.  Maintain health and metrics endpoints.  Update `observability/` with any new dashboards.
5. **Security** – Review authentication and authorisation logic.  Ensure bearer tokens are verified using a secret key and that sensitive routes enforce role/permission checks.  Run static analysis and dependency audits.  Harden supply chain by pinning versions and enabling Dependabot/Renovate.
6. **Testing** – Extend tests as features are added or refactored.  Write unit tests for new services, integration tests for database interactions, end‑to‑end tests covering HTTP routes and a load test profile.  Ensure coverage targets are met via `pytest --cov`.
7. **Documentation and handoff** – Update `README.md`, `ARCHITECTURE.md`, `RUNBOOKS.md`, `CONTRIBUTING.md` and `CODEOWNERS` as necessary.  At the end of the work include a **Work Log** section summarising the problem, root cause, solution, files changed, tests added, migration/rollback steps and residual risks.

## Blockers

If any requirement is ambiguous or cannot be satisfied, add a bullet point here describing the blocker, its impact, proposed resolutions and any minimal fallback path.  Do not proceed past the blocking point without acknowledging it with the owner of the work order.
* **Repository mismatch between project archive and this repository** – The codebase in this repository does not include the FastAPI application and database structure described in the project archive. The existing repository appears to be an AI ontology/automation project with different directories. Without the expected `src/app` package, single ASGI entrypoint or Alembic migrations, it is not possible to perform repository normalisation or implement the full stack. **Proposed resolution:** replace this repository’s contents with the provided project archive or create a new repository for the enterprise API. **Fallback:** document this mismatch and await guidance.
