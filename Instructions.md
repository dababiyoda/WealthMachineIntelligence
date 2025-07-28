# Implementation Instructions

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
