# Constitutional Control Layer

The Constitutional Control Layer is the part of the system that says **no**.
Everything else in WealthMachineIntelligence proposes, scores, and drafts;
this layer decides what any agent is actually allowed to do, records why,
and keeps the record where nothing can quietly rewrite it.

The doctrine in one line: **the machine prepares, the human authorizes, the
world responds, the system learns.** Nothing in this layer makes a venture
succeed. It makes failure visible, bounded, and reversible.

## Components

The layer lives in `src/control/` and has three parts:

| Component | Module | Role |
|---|---|---|
| Agent Contracts | `contracts.py` | The written, revocable scope of each agent's authority |
| Policy Evaluation Engine | `policy_engine.py` | Default-deny evaluation of every consequential action |
| Evidence Ledger + Assumption Register | `evidence_ledger.py` | Append-only memory of assumptions, evidence, and decisions |

## Agent Contracts

An agent has **no standing authority**. Whatever it may do is spelled out
in an `AgentContract`:

- **mission** — one sentence describing what the agent exists to do
- **autonomy_level** — 0–4, per `docs/PROGRESSIVE_AUTONOMY_LEVELS.md`
- **permitted_actions** — a whitelist of action types; everything else is denied
- **limits** — hard numeric ceilings (e.g. `max_spend_usd`)
- **prohibited_actions** — denied even if later added to the whitelist by mistake
- **escalation_triggers** — action patterns that always go to a human

Contracts are granted by a human, and:

- **new contracts cannot enter above autonomy level 1** — authority is
  earned in operation, not granted at birth;
- **revocation is immediate** and requires no evidence or process;
- every level change is recorded with its reason and evidence references.

## Policy Evaluation Engine

Every consequential action is described as an `ActionRequest` (agent,
action type, category, consequence, reversibility, spend) and evaluated.
The engine returns one of three verdicts:

- **allow** — inside the contract, the limits, and the autonomy level;
- **escalate** — legitimate but above the agent's authority; a human must
  approve before anything happens;
- **deny** — outside the contract or on a prohibited list; it does not
  happen.

The rules are **hardcoded doctrine, not configuration**, evaluated in
order:

1. **Globally prohibited actions are denied for everyone.** No contract
   can permit `self_authorize`, `modify_own_contract`,
   `raise_own_autonomy`, `disable_guardrails`, `bypass_policy_engine`,
   `delete_evidence`, `promise_returns`, or
   `personalized_financial_advice`.
2. **No contract, no authority.** Unknown or revoked agents are denied.
3. **The contract's prohibited list beats its own whitelist.**
4. **Default-deny.** An action type the contract does not explicitly
   permit is refused.
5. **Spend beyond the limit escalates.** Spend with no limit set also
   escalates — absence of a ceiling is not permission.
6. **Irreversible or high-consequence execution always escalates**, at
   every autonomy level. Level 4 is a ceiling, not an exemption.
7. **Autonomy gating.** Level 0 observes; level 1 may propose; execution
   starts at level 2 and is capped by consequence class per level.

Every evaluation — including allows — is appended to a decision log, so
the history of what was attempted (not just what happened) is
reconstructable.

## Evidence Ledger and Assumption Register

The ledger is append-only. Records are never edited or deleted; an
assumption changes status by appending a status event, so the path from
`untested` to `supported` (or `refuted`) is preserved.

It tracks four record types:

- **Assumptions** — beliefs the venture depends on, with criticality;
- **Evidence** — observations, marked `external` (the world responded) or
  `internal` (we told ourselves something). Only external evidence earns
  autonomy;
- **Experiments** — hypothesis, method, and result;
- **Decisions** — what was decided, by whom, on which evidence, and
  whether human approval is still pending.

Marking an assumption `supported` or `refuted` requires evidence
references — beliefs do not change for free.

## Where it is wired in today

The DALEOBANKS intake flow (`src/services/opportunity_intake.py`) routes
through the layer end to end:

- the intake agent operates under a **level-1 contract** permitting only
  `assess_opportunity`, with a spend limit of zero and `launch_venture`,
  `commit_capital`, and `publish_content` prohibited;
- every assessment is authorized by the policy engine before the venture
  loop runs;
- the packet's thesis enters the Assumption Register, its evidence items
  are recorded as external (weak) evidence, and the go/no-go lands as a
  decision that still requires human approval;
- `GET /api/ventures/{packet_id}/governance` returns the full trail:
  policy decisions, assumptions, and ledger events.

## What this layer does not claim

No policy engine makes ventures safe or profitable. Signals can be wrong,
models can be wrong, and approved actions can still fail in the world.
The claim is narrower: no consequential action happens outside a written
contract, above an earned autonomy level, or without a durable record.
