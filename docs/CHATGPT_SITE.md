# UAT ChatGPT Website

## Live surface

The published website is
[`UAT Venture Command`](https://uat-venture-command.investigatin-9078.chatgpt.site).

It makes the UAT doctrine reviewable without overstating the current system.
The landing experience explains the institution, its evidence-gated venture
lifecycle, twelve parent roles, operating guarantee, and current readiness
boundary. The command room is protected by ChatGPT-managed sign-in.

The current access policy is `custom` and allows the owner only. This is a live
production deployment, but it is not public internet access. The current
workspace makes `custom` and `workspace_all` available and does not offer a
`public` mode. Access must not be widened or described as public without a new,
explicit owner decision and a platform-supported access mode.

## Implemented website behavior

The website provides:

- a responsive institutional presentation;
- explicit disclosure that external autonomy is `none`;
- direct traceability to the governed-preview GitHub release;
- a ChatGPT-authenticated command overview;
- the current AG1/AG2 capability boundary and active bottleneck;
- an evidence register and portfolio hold state;
- a deterministic governed-action lab;
- responsive, keyboard-accessible navigation;
- fail-closed sign-in routing for the command room.

The action lab classifies a hypothetical request using action type, evidence
class, financial effect, reversibility, and bounded-outcome inputs. It returns
the minimum risk class, policy disposition, reasons, and next required proof.
It always displays and enforces this presentation-layer result:

> External side effect: Not executed.

## Separation from the control plane

The website is not the authoritative UAT runtime. It does not:

- connect to the FastAPI database;
- create identities, grants, approvals, claims, evidence, or audit records;
- receive production credentials or secrets;
- invoke external tools;
- spend, publish, deploy, contract, hire, or launch a venture;
- establish demand, compliance, security, or venture success.

The authoritative preview implementation remains in `src/governance/` and its
API surface under `/api/v1/governance`. The website communicates that model and
provides a safe operator-training interaction.

## Gates before a live API connection

Do not configure the website as a control-plane client until all of these are
demonstrated:

1. Deploy the exact reviewed FastAPI container behind TLS using immutable image
   provenance.
2. Replace preview identity with reviewed user-to-UAT identity mapping and
   server-side authorization.
3. Implement a policy-enforcing API or tool gateway with scoped, short-lived
   credentials and deny-by-default egress.
4. Use a production database with versioned migrations, encrypted backups, and
   a successful restoration exercise.
5. Add tenant and venture isolation tests.
6. Add server-side idempotency, reconciliation, rate limits, and complete
   telemetry for website-originated requests.
7. Complete threat modeling for cross-origin requests, session binding,
   replay, CSRF, prompt injection, malicious evidence, and confused-deputy
   behavior.
8. Complete independent security, privacy, legal, and recovery review.
9. Reconcile every external execution against independently verified final
   state.
10. Update `current-capability.json` only after the evidence is recorded.

Until those gates clear, the separation is a safety property—not missing
website polish.

## Release verification

The ChatGPT Sites release was built through its locked production pipeline and
verified as a deployed production URL on 2026-07-18. Its automated rendered
HTML checks confirm:

- the institutional doctrine and truth boundary render;
- an anonymous command-room request redirects to ChatGPT sign-in;
- an authenticated request renders the command room;
- the command room exposes the `external autonomy: none` boundary.

This verifies the website artifact. It does not clear any UAT production
acceptance gate by itself.
