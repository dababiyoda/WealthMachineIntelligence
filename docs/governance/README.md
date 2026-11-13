# UAT governance records

These records apply the Kernel's recursive collaboration protocol to PR #43. They consume the Kernel's canonical doctrine and do not restate it:
- `uniimente-kernel/docs/FOUNDER_INTENT_LEDGER.md`;
- `uniimente-kernel/docs/RECURSIVE_COLLABORATION_PROTOCOL.md`;
- `uniimente-kernel/docs/collaboration/START_HERE.md`.

WMI owns no constitutional interpretation, and nothing here grants authority.

| File | What it is |
|---|---|
| [`uat-intents.json`](uat-intents.json) | Eight founder intents from the master-plan conversation, each with a lifecycle state. |
| [`DELIB-WMI-UAT-001.json`](DELIB-WMI-UAT-001.json) | The deliberation on PR #43: five roles, two strengthening passes, preserved dissent. Decision: `NEEDS_FOUNDER_DECISION`. |

Both validate with the protocol's fail-closed checkers, `validate_intent_ledger.py` and `validate_deliberation.py`.

## The open decision: two UAT designs in WMI

Draft PR #15 (2026-07-18) specifies the Universally Adaptive Team as a twelve-parent-agent enterprise operating system for WMI. PR #43 (2026-10-22) implements the founder's later eight-role master plan as runnable code.

Both target one intended effect. PR #43 was built before the required search of open PRs. This page records the overlap instead of letting two products grow.

Recommended disposition: PR #43 becomes the first executable slice of #15's architecture. This is a recommendation, not a ruling. The founder names the canonical owner (intent `WMI-UAT-008`).

| PR #43 component | Maps to in PR #15 | Disposition |
|---|---|---|
| `src/services/uat_governor.py` (deterministic gate; a pass maps to VALIDATE, never COMMIT) | §7.4 Evidence and Decision Plane; §10 venture lifecycle and gates | Integrate |
| `src/services/uat_missions.py` (missions, handoffs, independent review, collections) | §9.2 Governance and evidence tables; §10.1 transition protocol | Integrate; its JSON-lines store is a stand-in for #15's PostgreSQL |
| `src/services/uat_swarm.py` (proof graded by reviewer lineage, standing decays) | §7.3 Parent Intelligence Council, requirement on correlated model failure | Integrate: it is the executable form of that requirement |
| `src/services/uat_store.py` (append-only, locked, replayed ledger) | §9.1 store responsibilities | Preserve until #15's authoritative store exists |
| `src/swarm/` runtime, local model route by default | §8.2 Model Assurance Service | Integrate under the Kernel's open-source-first intent |
| `src/swarm/railscout.py` (Kernel `opportunity-packet` outbox) | Organ exchange, outside #15 | Integrate; delivery awaits the founder (intent `WMI-UAT-006`) |
| The thirteen-bot group design (from the founder's files) | Venture Pod roles | Mechanisms extracted; the Grok form is not adopted |

## What is still owed

- **Kernel work-board claim.** The procedure asks for a claim on `uniimente-kernel#96` before editing. This session can read the Kernel repository but not its issues, so no claim was posted. A collaboration receipt is in the PR #43 body instead.
- **Buyer evidence.** None exists. A completed internal workflow is not buyer demand (founder, 2026-11-12).
