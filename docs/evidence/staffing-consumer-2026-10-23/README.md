# Staffing evidence: consumer integration, 2026-10-23

Observation: WMI previously counted the evidence without using the staffing figures. With equal evidence counts, a complete 8/8 plan, a 4/8 shortfall, and an assignment inconsistent with its claimed total could receive the same assessment treatment.

Implementation: the existing labeled staffing JSON now changes assessment reasons and the first validation step. A shortage, malformed report, inconsistent arithmetic or differing reports can tighten `go` to `needs_more_evidence`. A complete report does not promote a verdict. Every result is explicitly unverified.

The full parent remains **BODY + ORGANS + MIND = GREG / UNIIMENTE**, not this component. This is the bounded consumer deficit recorded by the integration owner on [the work board](https://github.com/dababiyoda/uniimente-kernel/issues/96#issuecomment-6364527789), claimed [here](https://github.com/dababiyoda/uniimente-kernel/issues/96#issuecomment-6366173923).

## Ownership and exact sources

| Item | Source |
| --- | --- |
| Implementer | Codex `/root`, workspace `a60f90b8f5e5`, task `wmi-staffing-evidence` |
| WMI base | #44, `7a45d223b74d6eea3b9ed5bdaeb12a3625b525de` |
| Real DALEOBANKS producer | #96, `664ac98c553759ce754bb684cb248225343edd7e` |
| Installed canonical boundary package | Kernel `e7dc0cbc9c9a9491da253deee018d471af5a77df` |
| Kernel integration inspected | #196, `a1c6dbcb2d5b4f1647b0f3569dbbbdf0aae558d3` |
| Separate license owner inspected | #201, `1698a87c0e05bf835a84dec95cfe5445111dccf0` |
| Proposed destination | Existing WMI #44 branch, then separately reviewed Kernel organ-pin integration |
| Integration owner | `session_01FBS4KNJR59nSbdGbxo8Mbx`; intake acknowledgment pending |
| Independent reviewer | Unassigned; pending |

No existing owner branch is edited. The change uses the existing strict assessment contract's reasons and validation_plan, with no shared schema, transport, pin or authority change.

## Validation

Evidence tiers are unit tests and synthetic localhost subprocess execution. No real demand, staffing deployment, independent outcome or commercial result is claimed.

- [before.txt](before.txt): **3 failed, 1 passed**, before the production change. The original failure output is preserved, including inherited engine/database logging.
- [after.txt](after.txt): **167 passed in 12.66s**, complete WMI suite with the exact real producer checkout. Python **3.12.14**; hosted CI uses Python 3.11 and must independently pass.
- [ablation.txt](ablation.txt): **3 expected behavioral failures** when only the new reader is replaced with an empty reader in a separate process. The production file hash is unchanged.
- New reader and both new test files pass Ruff. The edited intake file has no additional diagnostics compared with its base; its 27 inherited diagnostics remain.
- The real-producer test runs DALEOBANKS's actual `stated_evidence` and HTTP client against the Docker COPY/CMD composition. The signed response is consumed by the real producer. No route, JWT or scoring overrides are used.
- Existing packaged startup, signed-body refusal, restart, idempotency, replay and authority controls pass in the full suite.
- Initial environment failure: invoking the venv's Python without putting its executables on PATH made six existing startup tests unable to find `uvicorn` (160 passed). Correcting PATH addressed it without production edits.
- [after-first-packaging-run.txt](after-first-packaging-run.txt): the next full run had one TIME_WAIT bind failure in the new test (166 passed). The new test now matches uvicorn's socket-reuse behavior, while still refusing an active listener.

Reproduction, after installing the repository's CI dependency subset and exact boundary package:

```sh
PATH="<venv>/bin:$PATH" DALEOBANKS_SOURCE="<checkout at 664ac98c553759ce754bb684cb248225343edd7e>" \
  "<venv>/bin/python" -m pytest -q tests --show-capture=no --tb=short -W ignore
ruff check src/services/staffing_evidence.py tests/test_staffing_evidence.py tests/test_staffing_producer_consumer.py
```

The test refuses an occupied live port 5000. It never terminates another owner's service.

## Evidence and authority ceiling

The reader checks reported integers, assignment totals, unfilled totals and staffed + shortage = demand. It rejects duplicate JSON keys, nonfinite numbers, booleans used as quantities, incomplete JSON, repeated assignment pairs and oversized recognized reports.

Bounds: 8,192 characters per recognized report, 16 reports, 256 assignment rows and unfilled orders, 128 characters per identifier, quantities no greater than 10^12. Recognized excess/truncation stays unresolved. DALEOBANKS's existing extraction can truncate at 2,000 characters; a truncated recognized plan therefore receives an explicit unresolved result.

The original staffing problem is absent. The reader cannot verify worker capacity, eligibility, per-order original demand, optimum, provenance or actual availability. A coherent fabrication can pass arithmetic. A received `certified` flag and certificate remain claims; they confer no trust. Transport authentication is not domain verification.

Different reports can be alternative scenarios. The consumer asks to distinguish alternatives from contradictions against original inputs rather than inventing a contradiction.

Ordinary prose and other report formats retain the existing route. The opportunity score remains heuristic. Full evidence comprehension, calibrated business judgment and real acceptance are still separate requirements.

## Deliberation and handoff

[deliberation.json](deliberation.json) applies the Founder-Intent Collaboration Protocol: five explicitly labeled **self-review** perspectives, alternatives including do nothing and original-input recertification, exactly two strengthening passes, preserved dissent, residual risks, migration and rollback. This is a bounded specialist feature, with existing ownership, shared contracts and authority unchanged. Independent review is pending.

Decision: **EXPERIMENT**; retain as a reviewable draft, without claiming adoption or complete-machine closure.

Receiver's next action: review this exact child commit; adopt it into the existing WMI integration if accepted; repin WMI in Kernel under the existing owner; strengthen the 15-step step-9 assertions so actual reasons, shortage holds and validation priorities depend on the bound Mind answer; run the integrated mission and transport-negative controls. This must exercise the consumed answer, not merely assert that its bytes reached WMI.

After that adoption, resume the parent: original-input verification where required; per-organ asymmetric transport signatures; combined #201/#196 verification and receipt repair; outcome-backed learning and the other unclosed requirements in the existing canonical path. Those remain with their existing owners or need separate non-overlapping claims.

Rollback: revert only this component commit; if adopted, restore the previous WMI organ pin and rerun its integrated checks. Preserve the negative evidence and decision in history.

Stop this component if it weakens authority/legal floors, promotes a certificate claim to verification, needs an unreviewed shared-contract change, regresses the real producer, or collides with a new owner claim.
