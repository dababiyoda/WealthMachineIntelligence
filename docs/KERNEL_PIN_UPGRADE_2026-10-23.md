# Kernel boundary pin upgrade — 2026-10-23

Founder decision (2026-10-23, in the #196 session): "All organs should have upgraded pins."

## Pins

| What | From | To |
| --- | --- | --- |
| `uniimente-kernel-boundaries` (requirements, pyproject, CI) | Kernel `4999acff` | Kernel `e7dc0cbc` (head of uniimente-kernel draft PR #196) |
| CI's real DALEOBANKS producer | `18f1989c` | `664ac98c` (DALEOBANKS branch `claude/greg-full-machine-completion-whgiee`) |

The package version string stays 0.1.2, because the Kernel's frozen proof missions check it; the
pin is the commit.

## What the new transport gives this organ

- `build_headers` prefers `UNIIMENTE_BRIDGE_KEY_WEALTHMACHINE` over the shared
  `WEALTHMACHINE_SIGNING_KEY`, and binds the key scope into the signature.
- `verify_headers` checks an identity-scoped message against the claimed sender's own key, so a
  message signed with another organ's key is refused.
- When no per-organ key is configured, everything stays at shared scope, byte-identical to
  transport v2.

## What the new DALEOBANKS producer changes

DALEOBANKS's packets now carry the thought's stated evidence (sentences with figures) after their
provenance item, so `packet["evidence"]` reaches this organ's signals and its adversarial demand
case.

## Evidence

- Local suite on the new pins: 126 passed, the same as on the old pin.
- Two tests need port 5000, which this container holds: `test_exact_packaged_command_protected_bridge`
  and `test_real_producer_consumer_restart_and_negative_controls`. They are left to CI on this
  branch's draft PR.
- Merge to `main` remains the founder's decision.
