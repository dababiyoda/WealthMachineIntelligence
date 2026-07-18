# UAT Governed Preview

The repository now publishes one coherent preview of the Universally Adaptive
Team operating model: an evidence-labeled venture simulation wrapped in a
deterministic, deny-by-default governance and evidence workflow.

**Live institutional website:**
[`UAT Venture Command`](https://uat-venture-command.investigatin-9078.chatgpt.site)

The landing route explains the doctrine, architecture, lifecycle, roles, and
current readiness boundary. Its `/command` route uses ChatGPT-managed sign-in
and provides a deterministic governed-action lab. That lab never executes an
external action and is not connected to production venture or financial data.
See [`docs/CHATGPT_SITE.md`](docs/CHATGPT_SITE.md) for the integration boundary.

It is ready to review and deploy as a **governed preview**. It is not ready to
operate businesses autonomously.

## Current truth boundary

The preview can persist identities, contracts, capability grants, budgets,
claims, evidence, approvals, policy decisions, kill switches, human execution
records, outcome verification, and a hash-chained audit history. It can
reconstruct one proposed action from evidence through its final recorded state.

It cannot autonomously spend, publish, deploy, contract, hire, transfer money,
or launch a venture. External autonomy is `none`. R4 actions remain
human-execution-only even after all approval records exist.

The older venture engine remains a simulation and architectural skeleton.
Its market, financial, agent-performance, and heuristic-risk values are not
independently verified outcomes.

Historical numerical simulation modules are quarantined from the release
runtime. Developers who need to inspect that legacy path may install
`.[legacy-simulation]`; it does not add production authority or calibration.

The machine-readable truth boundary is
[`spec/uat/v1/current-capability.json`](spec/uat/v1/current-capability.json).

## Architecture contract

- Normative design: [`docs/UAT_ENTERPRISE_SYSTEM_SPECIFICATION.md`](docs/UAT_ENTERPRISE_SYSTEM_SPECIFICATION.md)
- Venture lifecycle: [`spec/uat/v1/venture-lifecycle.json`](spec/uat/v1/venture-lifecycle.json)
- Agent charters: [`spec/uat/v1/agent-charters.json`](spec/uat/v1/agent-charters.json)
- Approval matrix: [`spec/uat/v1/approval-matrix.json`](spec/uat/v1/approval-matrix.json)
- Threat model: [`spec/uat/v1/threat-model.json`](spec/uat/v1/threat-model.json)
- Preview control claims: [`spec/uat/v1/governed-preview-controls.json`](spec/uat/v1/governed-preview-controls.json)
- Release checklist: [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)

## Run locally

Python 3.11 or later is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
export DATABASE_URL=sqlite:///./uat-preview.db
uvicorn src.api.main:app --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000`.

Development enables two bounded local identities unless
`UAT_ALLOW_DEMO_USERS=false`:

- `admin` / `admin`: preview governor with API administration permissions;
- `demo` / `demo`: independent evidence reviewer.

These identities are prohibited in production by default. They receive only
R0/R1 analysis and sandbox capability when preview bootstrap is enabled.

## Run the release container

```bash
cp .env.example .env
# Replace every placeholder secret and set the public host/origin.
docker build -t uat-governed-preview:0.2.0-rc1 .
docker run --env-file .env -p 5000:5000 uat-governed-preview:0.2.0-rc1
```

Read [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) before exposing the preview.

## Governed action flow

1. Register a claim.
2. Attach source-bound evidence.
3. Independently verify consequential evidence.
4. Submit an action request referencing a valid contract and grant.
5. Let the deterministic policy service check identity, scope, evidence,
   minimum risk class, action window, budget, rollback, approvals, and kill
   switches.
6. Re-evaluate those controls immediately before accepting a human execution
   record.
7. Use a different human to verify the resulting external state.
8. Reconstruct the complete record through
   `GET /api/v1/governance/actions/{action_id}/reconstruction`.

The API workflow is documented in
[`docs/CONTROL_PLANE_PREVIEW.md`](docs/CONTROL_PLANE_PREVIEW.md).

## Principal endpoints

| Endpoint | Purpose | Authentication |
| --- | --- | --- |
| `GET /` | Operator console and public truth boundary | Public |
| `GET /health/live` | Process liveness | Public |
| `GET /health/ready` | Database and audit-chain readiness | Public |
| `GET /api/v1/system/capabilities` | Machine-readable capability limits | Public |
| `POST /auth/login` | Bounded operator authentication | Credential required |
| `GET /api/v1/governance/status` | Control/evidence-plane status | Read permission |
| `POST /api/v1/governance/actions` | Propose and policy-check an action | Write permission |
| `POST /api/v1/governance/kill-switches` | Activate containment | Incident permission |

Legacy venture and agent mutation endpoints are held with HTTP `409`; callers
must use the governance workflow.

## DALEOBANKS compatibility bridge

The existing `OpportunityPacket` intake contract remains available at:

- `POST /api/opportunities/intake`
- `POST /api/ventures/evaluate`
- `GET /api/ventures/{assessment_id}/assessment`

In production, the bridge fails closed until
`WEALTHMACHINE_INTAKE_TOKEN` is configured. Its output is a recommendation that
always requires human approval; it does not create or launch a venture.

## Verify

```bash
ruff check .
python -m compileall -q src main.py
node --check static/app.js
pytest -q
docker build -t uat-governed-preview:test .
```

GitHub CI repeats the test, lint, JavaScript syntax, package-integrity, image
build, and production-configured container smoke checks. Image publication is a
separate manual workflow requiring the exact confirmation phrase
`PUBLISH_GOVERNED_PREVIEW`; it reruns the release matrix before emitting only
commit-bound tags with provenance and an SBOM.

## What remains before broader authority

- independent AG0 review;
- complete AG1/AG2 review and immutable external audit anchoring;
- versioned production database migrations and tested restoration;
- AG3 isolated runtime, tool gateway, secret broker, and egress controls;
- one real, paid, bounded Venture Pod proving customer value;
- independent security, privacy, legal, reliability, and recovery assurance.

No README, dashboard, score, or passing test may be used to claim those gates
have already cleared.
