# Structural clarity audit — October 25, 2026

Decision: **RETAIN** the existing repository boundaries; consolidate WMI's duplicated dependency declarations through a generated compatibility export. This is a structural pass, not full-machine completion.

## Inspection scope

Ran the Founder-Intent Collaboration Protocol's inventory_repository.py and detect_exact_duplicates.py across the three local primary repositories. All six scans completed without truncation or errors. Scanned entries include documentation, fixtures and historical material; they are not authored-code counts. Cache/VCS/dependency trees are pruned by the tools. Local untracked material can appear in inventories; scan output is provisional, not an instruction to delete it.

Exact heads, provisional category counts, duplicate groups and hashes: [scan evidence](structural-scan-2026-10-25.json).

| Repository | Inventory entries | Exact duplicate groups | Role |
| --- | ---: | ---: | --- |
| Kernel | 2,409 | 35 | Constitutional controls, canonical contracts, evidence spine and persistent GREG runtime |
| DALEOBANKS | 274 | 2 | Specialist perception, media, audience and distribution organ |
| WMI | 209 | 1 | Specialist opportunity assessment and venture workflow organ |

Semantic inspection covered agent instructions, current work-board claims, Kernel #196, WMI open PR metadata, WMI package/dependency manifests, Docker composition, application entry points, compatibility adapters, selected orchestration interfaces and all duplicate Python groups. Prior project-source reading supplies intent context; it is not code-coverage evidence for this pass.

This is not a claim to have read every line, every historical branch, every open PR implementation or every secondary repository. RailScout, PumpStation, RESEARCH-IN and separate Foundry repositories have not received fresh structural scans in this pass. Their consolidation must wait for equivalent owner/import/build evidence. Do not generalize these counts to the whole account.

## Ownership and boundaries

| Mechanism | Canonical owner / interface | Disposition |
| --- | --- | --- |
| Institutional authority and canonical wire contracts | Kernel; organs import the pinned boundary package | Preserve; do not consolidate authority into an organ |
| WMI web runtime | src/api/main.py; root main.py compatibility import | One active application; root Docker uses a positive source allowlist |
| WMI Enhanced generation | WealthMachineIntelligenceEnhanced/ | Experimental; excluded from root image; preserve distinct code until capability comparison |
| Previous root implementation | historical/ | Evidence, outside runtime import surface |
| Transport and schema translation | Kernel adapters; WMI compatibility modules point to it | Intentional thin shims, not duplicate security engines |
| Specialist opportunity reasoning | WMI; DALEOBANKS produces signals and consumes recommendations | Preserve organ responsibility; assess shared adversarial logic separately before extracting it |
| Runtime dependencies | WMI pyproject.toml | Single authored list; requirements.txt becomes a generated Docker/pip export |

Testing boundary: two dependency-manifest tests exercise the committed export and non-writing stale detection. Existing WMI CI discovers them. No external effect, deployment, dependency version, solver behavior, signed gate or organ pin changes.

## Findings and dispositions

1. **Implemented: redundant dependency declarations.** requirements.txt had 40 declarations for 20 packages. The first 20 matched project.dependencies; the remainder repeated package names without useful additional constraints. The new exporter preserves every exact bound, extra and content-pinned Kernel URL. It adds no runtime dependency and leaves Docker's existing input path intact. Edit pyproject.toml, run `python scripts/export_requirements.py`, then `--check` to verify freshness.
2. **Implemented: runtime navigation.** README's directory guide emphasized design folders without distinguishing the actual src runtime, root compatibility import, experimental Enhanced tree and historical code. A concise ownership note now names those boundaries and the dependency workflow.
3. **Retained: frozen evidence copies.** Kernel run_v2.py/run_v3.py copies under the pr158 lineage archive match active evaluation files. That proves identical bytes, not redundant evidence. Content-addressed repair objects matching policy source serve recovery provenance. Do not replace either with imports or links: later source edits must not rewrite the historical snapshot's meaning.
4. **Retained: captured founder/source text.** DALEOBANKS's two duplicate groups and WMI's one group are attached source-text captures. Removing captures offers negligible runtime clarity and loses independent source locations. Leave them out of authored-code cleanup conclusions.
5. **Deferred: repeated evidence-table generators.** Two admission-run make_readme_tables.py files match. They live with separate evidence runs. A shared future generator could reduce maintenance, but retroactively redirecting old run scripts would impair reproduction. Extract only for new runs, with generator revision pinned per run.
6. **Deferred: semantic duplication.** DALEOBANKS and WMI retain specialist adversarial/scoring paths, while WMI has several orchestration abstractions. Similar names or shapes do not prove substitutability. Trace actual callers and compare outputs before extracting shared logic; do not merge distinct workflow, phase gate and rule-engine responsibilities merely for fewer files.
7. **Follow-up: documentation drift.** Instructions.md contains dated source pins and older readiness observations. Treat those as historical evidence; current runtime and package manifests win. A future documentation pass should split current operator instructions from dated proof records, preserving their stable links. Do not bulk-rewrite historical claims as current truth.

## Five perspectives — explicit self-review

All five perspectives below are one Codex worker's self-review, not independent approval.

| Role | Position and material concern |
| --- | --- |
| Founder-Intent Steward | Preserve BODY + ORGANS + MIND and the broad computer/tool/worker horizon. Fewer files is not success if useful capability or evidence disappears. |
| Systems Architect | Keep Kernel authority and specialist organ ownership. Consolidate the authored dependency list, not the repositories or separate orchestration semantics. |
| Adversarial Reviewer | Hash equality does not establish safe deletion. Check version bounds, extras and pinned URLs; a generator must detect drift without rewriting files in check mode. |
| Operator and Maintainer | Make current runtime and maintenance commands obvious. A small stdlib exporter is easier to maintain than repeated manifests or a new build framework. |
| Evidence and Welfare Guardian | Keep negative results, archives, source captures and precise inspection limits. No commercial, operational or whole-project completion claim follows from this cleanup. |

## Strengthening pass 1

Target: reduce maintenance ambiguity without changing dependency resolution or application behavior. Baseline repeats metadata manually. Doing nothing retains known drift risk. Simplest alternative removes the trailing duplicate lines, but still leaves two authored lists. Strongest competing approach changes Docker to install the project directly, which changes build/install composition and broadens this pass. Selected reversible approach keeps the existing requirements interface and generates it from project.dependencies.

| Downside | Redesign |
| --- | --- |
| D1: generator becomes another maintenance burden | Use only Python 3.11 stdlib, one command and a short freshness check; no new framework |
| D2: generated export might alter dependency semantics | Compare every original requirement against canonical package name, bound, extra and URL before adopting |
| D3: broad deduplication could erase history or distinct behavior | Classify matches and trace consumers; retain evidence, archive and recovery copies |

Rejected alternative: collapse Enhanced into the root application. Revive only after comparison proves which distinct capabilities should migrate and startup/authentication parity passes.

## Strengthening pass 2

Attack: check mode could silently rewrite stale files; a shared generator could change old evidence; structural counts could be mistaken for semantic coverage. Strengthening: test non-writing drift refusal, scope the exporter only to current packaging, retain frozen scripts, and state the scan and semantic limits explicitly.

| Downside | Disposition | Owner / review trigger |
| --- | --- | --- |
| D1 | Accepted: one small exporter and a generated header are the minimum interface cost | WMI maintainer; review if packaging adopts a direct project-install workflow |
| D2 | Resolved for inspected manifests: all 20 package requirements preserved, 20 redundant declarations removed | WMI maintainer; check export whenever project.dependencies changes |
| D3 | Resolved for this change: no archive, evidence, authority or runtime implementation removed | Integrator; reopen only with lineage and caller evidence |

Residual risks: other branches may add dependencies and must regenerate after integration; full runtime/image tests remain separate from manifest conformance. Independent review is pending. Dissent retained: a direct project install could eventually remove the generated interface entirely, but it needs a separately tested Docker migration.

## Validation, migration and rollback

Executed: two stdlib unittest checks pass; all 20 original package constraints/extras/URLs match canonical metadata; 20 redundant declarations removed. Run `python -m unittest discover -s tests -p test_runtime_dependency_manifest.py -v` and `python scripts/export_requirements.py --check`.

Dedicated WMI child branch on #45 b2c7f234; #44 and its integration owner's branch remain untouched. Claim: Kernel board comment 6398765840. Review unassigned; existing integration owner session_01FBS4KNJR59nSbdGbxo8Mbx receives the exact-head draft. No merge or deployment authority is granted.

Rollback: revert this cleanup commit. No data migration or state change exists. Kill the change if dependency semantics differ, the existing packaging interface breaks or another live claim overlaps. Next structural work should address demonstrated caller-level duplication and current-instruction discoverability, rather than deleting evidence to improve file counts.
