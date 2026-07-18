# Security Policy

## Supported artifact

Only the current governed preview release candidate is supported. Historical
deployment and probability claims are non-normative.

## Reporting

Do not place credentials, personal data, exploit payloads, or regulated data in
a public issue. Contact the repository owner privately and include the affected
commit, component, reproduction conditions, and potential impact.

## Current security boundary

- external autonomy is disabled;
- production requires an explicit JWT secret and operator identity;
- demo users are disabled in production by default;
- legacy mutation routes are held;
- action authorization is deterministic and deny by default;
- requesters cannot lower the preview's deterministic minimum risk floor;
- authorization is re-evaluated before a human execution record is accepted;
- R4 remains human-execution-only;
- audit records carry an application-enforced hash chain that is not yet
  independently anchored;
- a non-root container and restrictive response headers are used.

The preview console keeps its bearer token in browser session storage. Deploy
it only in a controlled review environment with no third-party scripts. Replace
this preview identity flow with enterprise federation, phishing-resistant
authentication, and a reviewed session design before broader exposure.

These controls do not establish invulnerability or complete enterprise
security. The open limitations in `spec/uat/v1/current-capability.json` remain
part of the security model.
