# Progressive Autonomy Levels

Autonomy in this system is **earned, bounded, and revocable**. Agents and
Venture Cells hold an autonomy level from 0 to 4 recorded in their
contract, and the Policy Evaluation Engine enforces it on every action.
No level exempts an agent from human approval on irreversible or
high-consequence actions.

## The ladder

| Level | Name | May do | May not do |
|---|---|---|---|
| 0 | **Observe** | Read, analyze, monitor | Propose, execute, spend |
| 1 | **Propose** | Everything in 0, plus draft proposals and assessments for human decision | Execute anything, spend anything |
| 2 | **Execute-reversible** | Everything in 1, plus execute *reversible, low-consequence* actions within contract limits | Medium/high-consequence, hard-to-reverse, or irreversible actions; over-limit spend |
| 3 | **Execute-bounded** | Everything in 2, plus reversible *medium-consequence* and hard-to-reverse actions within limits | High-consequence or irreversible actions; over-limit spend |
| 4 | **Conditional** | Reserved. Same execution ceiling as 3 | High-consequence and irreversible actions still escalate — level 4 is a ceiling, not an exemption |

The consequence and reversibility of an action are declared on the
`ActionRequest` and judged by the engine; "escalate" always means a human
(or dual control) must approve before anything happens.

## Non-negotiables

1. **Every new contract starts at level 0 or 1.** The registry rejects
   anything higher at registration time. There is no senior-agent
   exception and no grandfathering.
2. **Promotion requires documented external evidence.**
   `ContractRegistry.set_autonomy_level` refuses an increase without
   evidence references pointing into the Evidence Ledger, plus a written
   reason. Internal model output does not count as evidence — the world
   has to have responded.
3. **Demotion is immediate and free.** A decrease needs only a reason.
   Regression must never be slower than promotion: when metrics degrade
   or trust is in question, the level drops first and the discussion
   happens afterward.
4. **Revocation is the kill switch.** A revoked contract fails every
   policy check instantly. No wind-down privileges, no grace period.
5. **Every level change is logged** — old level, new level, reason,
   evidence references, who changed it, and when. The history is
   append-only and reconstructable.

## What promotion evidence looks like

Evidence that can support a promotion request:

- externally validated assumptions (customers paid, replied, signed up —
  recorded as `external` evidence in the ledger);
- a run of policy-compliant operation at the current level (the decision
  log shows allows and escalations, no denied attempts to exceed scope);
- concluded experiments whose results matched their hypotheses;
- clean red-team results for the scope being requested (Phase 2+).

Evidence that supports nothing: enthusiasm, internal projections, time
elapsed, or the inconvenience of escalation.

## What triggers demotion

- degrading venture metrics or missed validation gates;
- denied policy checks showing attempts to act outside contract;
- an incident, near-miss, or red-team finding touching the agent's scope;
- operator judgment. No justification threshold applies — doubt is
  sufficient.

## Current state

As of Phase 0, the only contracted agent is `opportunity_intake` (level
1: it proposes assessments, executes nothing, spends nothing). Venture
Cells (Phase 1) will each carry their own contract and start at level 0
or 1 like everything else.
