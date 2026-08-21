# Phase 7 — First Digital Business Loop + Regenerative Treasury

Status: **executable and verified (2026-07-20)** — `src/services/business_loop.py`,
`src/services/treasury.py`, `tests/test_business_loop.py`,
`tests/test_treasury.py` (13 tests green).

## The loop

One complete, bounded circuit from signal to settlement:

    opportunity (kernel-format packet) -> validation gate -> offer construction
    -> human gate -> simulated settlement -> treasury waterfall -> reconciliation
    -> learning record

- only a `go` verdict proceeds; defer/kill/needs_more_evidence are records, not exceptions
- offers are bounded, reversible, honest — irreversible offers refuse
- the human gate is structural: no ratifier, no offer leaves
- settlement is **simulated** (a rehearsal of the money path) until the operator
  wires real rails through the kernel Consequence Gate
- every stage is recorded; the loop closes with a learning record

## The Regenerative Treasury waterfall

Revenue flows through one waterfall, in priority order, as a policy decision —
never an autonomous fund movement:

1. **operating costs** — the machine keeps itself alive
2. **reserve floor** — an absolute survival buffer, funded before any distribution
3. **regenerative share** — a floor, not a ceiling (minimum 10%); regeneration
   is not optional
4. **founder distribution** — last, and only what remains

Invariants: negative revenue refuses; shares never exceed 1.0; rounding
remainders go to reserve, never the founder; every plan carries
`requires_human_approval: true` and `execution_authority: false`.

## Kernel contract consumption (issue #27)

`src/services/kernel_contracts.py` is the single mapping point between the
kernel's canonical contracts (vendored, SHA-256 pinned under
`contracts/kernel/`) and the DALEOBANKS transport dialect. Kernel→wire is
documented lossy; wire→kernel is enriching and fails closed without the
mandatory kernel fields. Parity evidence: `tests/test_kernel_contract_parity.py`.
