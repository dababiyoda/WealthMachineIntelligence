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
| Python 3.11 CI | GitHub CI run 34109801918 completed successfully on e865a82 | Remote CI; distinct from local counts |
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

The staged source check was:

```
git diff --cached --check -- . ':(exclude)historical/**' ':(exclude)tests/evidence/**'
```

Full-tree whitespace warnings are retained because raw
evidence and historical implementation text intentionally retain their whitespace.
Local packaging command: `python -m pip install --no-deps --no-build-isolation
--target /workspace/scratch/c1c408c41c36/tmp/wmi-package-check -e .`.

Gate result: local WMI authentication/startup composition demonstrated. No global
security, durable replay, full schema validation, isolated workload identity, or
runtime integration gate passes by inheritance. Shared-primitive work comes next;
activation remains prohibited. PR #94 and its Kernel baseline failures are untouched.

## Published candidate and source binding

[Draft WMI PR #33](https://github.com/dababiyoda/WealthMachineIntelligence/pull/33)
contains implementation commit `e865a82c3611a4ba06445c9fc07938af0aecaebf`.
Uploaded source tree `b4e702e36a57366d2c15ce7ef80ade0d55fc4f2f` exactly matches
the locally staged tree. The subsequent evidence-only update does not change code.
[CI run 34109801918](https://github.com/dababiyoda/WealthMachineIntelligence/actions/runs/34109801918)
was observed completed/success for that implementation commit; this does not
retroactively establish Docker-image evidence or any institutional outcome.
Kernel #94 was rechecked: draft, unmerged, head
`5e2f221b1911309db10de26246065553c1bdcbfc`, still targeting Phase 3.

Next-package inspection begun (PR metadata/body evidence, not new execution):

| Source | Inspected head | Disposition |
| --- | --- | --- |
| Kernel #71 | 2221705421eed655e5edcb0608593cdf9d3cd72b | Extract canonical transport/identity precedents; runtime remains competitor |
| Kernel #87 | dfd491d8b34fa963e4902008b5d8dc7690fdde63 | Extract grant/ledger/replay repairs; do not adopt whole branch |
| Kernel #85 | d611771a38b2679f6f8b5c6c57e819ff0d433b53 | Extract verifier subject-binding, not proof of measured content by itself |
| Kernel #93 | 21fb21ed803f43e47acb8e6420f6cdc4f74925cd | Extract local integrity checks; benchmark founder loop, not canonical runtime |
| DALEOBANKS #71 | a13f279210c3dc9722a61c1714b17b064a8c05c8 | Compare stricter explicit unsigned opt-in; not activated |
| DALEOBANKS #74 | ecbb4b744b69f8ea16ed38ba2f0711c1969547b5 | Compare transport parity; preserve reported 12 environment failures |

These inspections do not complete the shared-primitive package. No Kernel,
DALEOBANKS, runtime or other organ source was modified by this WMI package.
