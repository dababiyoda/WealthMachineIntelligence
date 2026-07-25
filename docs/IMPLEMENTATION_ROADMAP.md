# Implementation Roadmap: Doctrine-Compliant Venture Studio OS

Goal: evolve WealthMachineIntelligence from a prototype into a governed
venture studio operating system that supports progressive, bounded
autonomy inside Venture Cells while complying with the doctrines.

No part of this roadmap claims to remove risk. The system's job is to
make risk explicit, bounded, and reversible — not to promise outcomes.

## Current state

Foundation that exists:

- 8 role definitions; Income Streams Loop and Team Loop concepts
- Opportunity intake + VentureAssessment flow (`venture_protocol.py`)
- Risk flags and hardcoded `requires_human_approval: true`
- Multi-agent architecture, API, database, tests, Docker setup
- **Phase 0 (this work): Constitutional Control Layer** — policy engine,
  agent contracts, Evidence Ledger + Assumption Register, wired into the
  intake flow with a governance audit endpoint

Known gaps (ordered by phase below):

- No Venture Cell concept or isolation
- No mandatory red-team step in workflows
- No Portfolio Command layer or Human Authority Board routing
- No automated autonomy regression on metric degradation
- Persistence for contracts/ledger is in-memory (interfaces are stable;
  storage engine comes later)

## Phase 0: Foundation — delivered

**Priority 1 — Constitutional Control Layer** (`src/control/`)

- [x] Policy Evaluation Engine (`policy_engine.py`): default-deny
      evaluation of `ActionRequest`s; allow / escalate / deny verdicts;
      globally prohibited actions no contract can permit; append-only
      decision log
- [x] Agent Contract schema (`contracts.py`): mission, permitted
      actions, limits, prohibited actions, escalation triggers; new
      contracts capped at level 1; promotion requires evidence; demotion
      and revocation immediate
- [x] Assumption Register (part of `evidence_ledger.py`)

**Priority 2 — Evidence Ledger**

- [x] Append-only ledger of assumptions, experiments, evidence, and
      decisions (`evidence_ledger.py`)
- [x] Integrated with the opportunity flow: thesis → assumption,
      packet evidence → external evidence records, go/no-go → decision;
      `GET /api/ventures/{packet_id}/governance` exposes the trail

**Priority 3 — Documentation alignment**

- [x] `docs/CONSTITUTIONAL_CONTROL_LAYER.md`
- [x] `docs/PROGRESSIVE_AUTONOMY_LEVELS.md`
- [x] README updated to the doctrine-aligned framing (no risk-elimination
      language)

## Phase 1: Venture Cells & Isolation (weeks 3–5)

- Venture Cell data model and charter structure (mission, budget,
  autonomy level, kill switch, scoped permissions)
- Cell provisioning: isolated namespace, its own `AgentContract`,
  budget ceiling, kill switch wired to contract revocation
- Autonomy levels 0–4 enforced per cell by the existing policy engine
- Opportunity flow may propose cell creation after sufficient external
  evidence — creation itself is a human-approved, escalated action

Non-negotiable: every new cell starts at level 0 or 1 (already enforced
by `ContractRegistry.register`); every level change is logged with
evidence (already enforced by `set_autonomy_level`).

## Phase 2: Red-Team Integration & Portfolio Command (weeks 6–8)

- Mandatory red-team step before capital commitment, launch, or any
  autonomy increase past level 2; findings recorded in the Evidence
  Ledger
- Portfolio Command view: active cells, autonomy levels, key metrics,
  risk flags, pending escalations
- Kill switch / pause per cell (revocation + resource teardown)
- Human Authority Board workflow: routing of high/irreversible
  escalations to named humans with dual control on capital

## Phase 3: Advanced Governance & Hardening (weeks 9–12)

- Evidence Ledger with persistent storage, provenance, and full
  reconstruction
- Hard separation between the Permanent Intelligence Council
  (studio-level agents) and Venture Cells
- Automated autonomy regression when metrics degrade
- Expanded red-team catalog: model attacks, business-logic attacks,
  governance bypass attempts
- Comprehensive audit logging and reporting

## Success criteria for "doctrine-compliant"

- Every consequential action routes through policy evaluation
- Agents hold explicit contracts with limits
- Venture Cells are isolated and start at low autonomy
- Autonomy increases only with documented external evidence
- High-consequence actions require human approval or dual control
- Red-teaming precedes major decisions
- A cell can be paused or killed immediately
- Documentation makes no "foolproof" or guaranteed-outcome claims
