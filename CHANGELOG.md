# Changelog

## 0.2.0-rc1 — 2026-07-18

- Added a persistent AG1/AG2 control-and-evidence vertical slice.
- Added deterministic R0-R4 policy checks, dual approvals, budgets, kill
  switches, reconstruction, human execution records, and independent outcome
  verification.
- Added a deterministic minimum risk floor, action-window enforcement, current
  approval checks, and immediate reauthorization before human execution
  records are accepted.
- Added an application-enforced SHA-256 audit hash chain and tamper-detection
  regression tests; independent immutable anchoring remains open.
- Consolidated the application to one FastAPI entrypoint.
- Removed automatic browser demo login and external UI assets.
- Disabled direct legacy venture and agent mutations.
- Added fail-closed production identity and DALEOBANKS token configuration.
- Reduced the publishable container to bounded runtime dependencies and a
  non-root user.
- Added production-configured container smoke tests and a manually authorized
  GHCR publication workflow that reruns release gates and emits commit-bound
  tags, provenance, and an SBOM.
- Added a locked dependency graph and CI vulnerability audit; removed the
  vulnerable JOSE dependency from the preview token path.
- Published the UAT Venture Command ChatGPT website with an owner-access
  institutional surface, D1-backed Egregore and activation-intent records,
  ChatGPT-managed sign-in, and a deterministic no-execution action lab.
- Represented DALEOBANKS as a separate schema-1.0-compatible sibling service
  and LIVE PLAYER as unresolved agent context with authority `none`; neither is
  connected to production execution.

This release does not enable autonomous external actions or claim that AG1,
AG2, production, security, or enterprise assurance gates have cleared.
