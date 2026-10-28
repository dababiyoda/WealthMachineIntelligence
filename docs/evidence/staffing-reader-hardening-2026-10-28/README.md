# Staffing reader hardening — evidence, 2026-10-28

A child of WMI #45 (`b2c7f234`, Codex a60f90b8f5e5). It does not edit #45's branch. Implementer: Claude Code cloud session `session_01Kucyfoabgsg6W8H8xj4qea` (Kernel #96 claim 6473380596). The review was independent of #45's author; the deliberation is self-review.

## What WealthMachine does now that it did not do on #45

- **A staffing report no longer counts as demand.** On #45, adding an 8/8 report turned `defer` into `go` at low urgency (opportunity score 0.638 → 0.667). A second rendering of the same report pushed it to 0.756. Recognised reports now stay out of the engine's demand signals and the adversarial evidence count. The score and the cases are the same with or without a report. The report can only change reasons, the validation plan and the go cap.
- **The report's own arithmetic is checked, including its bottleneck.** These are the guarantees the Kernel's `certify_staffing` makes for every answer it emits:
  - `certified` is true and a certificate object is present;
  - the bottleneck is null exactly when nothing is short;
  - otherwise its demand minus capacity equals the shortage, every unfilled order is one of its orders, those orders are served only by its eligible workers, and their units equal its capacity.

  A report that breaks any of these is unresolved. On #45, a fully staffed report whose own bottleneck said capacity was short read as "internal arithmetic agrees" and stayed `go`.
- **Recognition matches the real producer.** DALEOBANKS starts a new sentence only after `.`, `!` or `?`.
  - A label after unpunctuated prose, two reports in one thought, and a report followed by a period are each read.
  - Trailing text after a report is named, not ignored.
  - The label is matched in any case and with either apostrophe.
  - Staffing-shaped JSON under another label is unresolved; it is not read as demand prose.
  - Tests use the Kernel's real rendering: `json.dumps(sort_keys=True, indent=1)`, so the JSON spans several lines.
- **Replays and rival plans are named.** A report that repeats an earlier one in any rendering counts once and holds `go`. Two different plans with the same figures, or the same plan with different short orders, must be reconciled first.
- **Unresolved reports rank first**, before shortages, which rank before complete reports, whatever the wire order. Identical steps appear once.
- **Classification depends on the report only.** Depth (at most 8) and number length (at most 13 digits) are checked by a scan before parsing. Neither Python's recursion depth nor its integer-digit limit can change a reason, and the Kernel compares reasons across two processes.

Nothing here verifies demand, capacity, optimality or the world. Every reading says "unverified report". `requires_human_approval` stays true, and the reader can only lower `go`.

## Evidence (exact revisions and commands are in each file's header)

| File | Result |
|---|---|
| `before.txt` | The 46 new tests on #45's reader: 35 fail and 11 pass. The 11 guard behaviour #45 already had right; the review showed those guards could be removed without any test failing. |
| `after.txt` | 46 of 46 pass on this branch. |
| `mutants.txt`, `run_mutants.py` | 28 of 28 guard-removal mutants are caught. The set includes the review's survivors M09, M12, M14, M19, M21, M22, M24 and M36. |
| `suite.txt` | Full WMI suite: 211 passed, plus the 2 port-5000 tests run alone (213 of 213). Ruff is clean on new and edited files. Intake diagnostics are identical to `b2c7f234` (27 inherited). |
| `deliberation.json` | Five roles, exactly two passes, validated by the protocol's `validate_deliberation.py`. Decision: EXPERIMENT. |
| `tests/fixtures/staffing/kernel_certified_answers.json` | The Kernel's own `certify_staffing` answers at Kernel `4e970f2d`: 8/8, 4/8, and the fifteen-step mission's 8 of 9. |

Environment: Python 3.11.17, as WMI CI uses. DALEOBANKS checkout `664ac98c` via `DALEOBANKS_SOURCE`. Boundaries pin `e7dc0cbc`. Linux cloud container.

The Kernel side is on draft child branch `claude/wmi-staffing-figures-step9-20261028` of #196. There, the same answers travel the real organ exchange. On WMI `7a45d223` (the current pin), 8/8 and 4/8 give byte-identical assessments, both `go`. On this branch they differ in their reasons and first step, with identical scores.

## Errata for #45's own records (preserved, not rewritten)

- `before.txt` there is fail-before evidence for an earlier 4-test draft, not for the committed 38 tests. Its line numbers and its warning counts do not match the documented command.
- `ablation.txt` there hashes `opportunity_intake.py`, not the reader it ablated. Its three tests were hand-picked and their selection is not recorded. An empty reader actually fails most of the committed tests.
- The size ceiling there is stated as DALEOBANKS's 2,000 characters. The real ceiling is earlier: the Kernel bind's `max_bytes` 2000 applies to the JSON-escaped seed, so the indentation newlines and quotes count twice. A larger plan is refused at the bind, and no assessment exists.
- The producer test there runs DALEOBANKS's `stated_evidence` and its HTTP client in WMI's interpreter, on a WMI-built packet. That packet has high urgency and no risk flags, unlike the real DALEOBANKS packet (medium urgency, `finance_education_only`). The Kernel child's contrast test runs the real `IdeaRefinery` on the mission's seed template.

## Limits and open items

- A consistent fabrication still reads as consistent. Only internal arithmetic is checked. An original-input reference in the packet is the precondition for recertification, and it needs the Kernel contract owner.
- Prose that names the label without carrying a report becomes an unresolved report. This is a deliberate, recorded dissent: the only producer of the phrase is GREG's seed template.
- DALEOBANKS's offline mock evaluator does not read staffing figures, so it now disagrees with WMI on a shortage. This is recorded for the DALEOBANKS owner and not changed here.
- Skeptic verification of the review findings was still running at commit time. Its verdicts are posted on the PR. A refuted finding is re-examined, and its fix is reverted if it is unjustified.
- No hosted CI result yet, no independent human review, no integrator acknowledgment, no merge.
