# WMI authentication / packaged startup evidence

Date: 2026-09-07. Base: ec84b6a2eec4efbc07bed7f167da81f5e25d890c.
Branch: agent/wmi-auth-packaged-startup-recovery. Disposition: draft candidate.
Ownership, intent, mechanism extraction, dissent and handoff: ../../../Instructions.md
(repository root Instructions.md; not a new governance program).

| Check | Actual result | Evidence tier |
| --- | --- | --- |
| Untouched baseline suite | 83 passed | Local tests; insufficient auth coverage |
| First auth negative controls against baseline | 30 failed, 2 passed | Retained negative controls, not 30 distinct exploit claims |
| Focused final (auth, subprocess startup, signed bridge, intake) | 69 passed, 304 warnings | Unit plus synthetic local subprocess HTTP |
| Broader final | 126 passed, 424 warnings | Local Python 3.12 tests |
| Existing pinned Kernel contract parity tests | 9 passed | Existing partial structural/parity checks, NOT full canonical schema validation |
| Focused changed-source lint | passed after recorded fixes | Static check |
| Authored-source staged whitespace check | passed | Excludes retained raw history/logs |
| Full staged whitespace check | reports pre-existing whitespace in preserved root snapshot and raw failure logs | Preserved, not normalized away |
| Editable package build/install, no dependencies/build isolation | passed into temporary target | Local packaging check, not image build |
| Tracked bytecode | 56 to 0 | Git inventory; original blobs retained |
| Docker image build / run | NOT RUN: Docker unavailable | Evidence gap |
| Python 3.11 CI | NOT VERIFIED locally | Evidence gap |
| Real founder authentication / CMC / external outcomes | Not established; CMC remains 0 | No claim |

The startup test copies exactly the Dockerfile COPY inputs into a fresh temporary
directory and runs its exact CMD with a synthetic SQLite database, test-only JWT
and HMAC material. It makes real localhost HTTP requests; no auth dependency or
route is replaced. This establishes source/CMD composition, not image build parity
or production-key custody. Every test process is shut down. No service is deployed.

Dependencies were installed into an isolated scratch target; command prefix:

```
PATH=/workspace/scratch/c1c408c41c36/tmp/wmi-test-deps/bin:$PATH
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=/workspace/scratch/c1c408c41c36/tmp/wmi-test-deps
```

Main versions exercised: Python 3.12, python-jose 3.5.0, cryptography 50.0.1,
FastAPI 0.141.1, Starlette 1.6.0, httpx 0.28.1, SQLAlchemy 2.0.52,
Uvicorn 0.52.4, pytest 9.1.1. Existing broad dependency ranges and heavy optional
image dependencies were not frozen or certified by this repair.

Raw stage logs retain initial 30 failures, the 10 fixture-migration failures,
and the packaged readiness failure. That failure was HTTP 400 from TrustedHost
because the harness used 127.0.0.1 in production mode; switching its request host
to the existing allowed localhost fixed the harness, without changing host policy.
Warnings remain visible. Lint also found one import-layout issue after adding the
last six controls; formatting was fixed and lint rerun, not ignored.

The staged source check was `git diff --cached --check -- .
' :(exclude)historical/**' ' :(exclude)tests/evidence/**'` with no spaces before
the two pathspec colons. Full-tree whitespace warnings are retained because raw
evidence and historical implementation text intentionally retain their whitespace.
Local packaging command: `python -m pip install --no-deps --no-build-isolation
--target /workspace/scratch/c1c408c41c36/tmp/wmi-package-check -e .`.

Gate result: local WMI authentication/startup composition demonstrated. No global
security, durable replay, full schema validation, isolated workload identity, or
runtime integration gate passes by inheritance. Shared-primitive work comes next;
activation remains prohibited. PR #94 and its Kernel baseline failures are untouched.
