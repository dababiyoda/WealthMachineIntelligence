# UAT Governed Preview Release Checklist

Release: `0.2.0-rc1`

The code can be published only when every machine-verifiable item is green and
the human items have named owners. Unchecked human items are explicit holds.

## Automated evidence

- [ ] Every entry in `governed-preview-controls.json` names implementation,
      executable tests, scope, and limitation.
- [ ] Full test suite passes for the exact commit.
- [ ] Governance and adversarial test suite passes.
- [ ] Ruff reports no violations.
- [ ] Python compilation and browser JavaScript syntax checks pass.
- [ ] Package dependency integrity check passes.
- [ ] Installed dependency vulnerability audit reports no known finding.
- [ ] Container image builds as a non-root user.
- [ ] Production-configured container passes liveness and readiness.
- [ ] Public capability endpoint states external autonomy is `none`.
- [ ] GitHub compare shows the release branch contains only intended commits.

## Human authorization

- [ ] System Governor confirms the capability record is truthful.
- [ ] Security owner reviews open limitations and deployment secrets.
- [ ] Data owner approves the database, retention, and backup location.
- [ ] Legal owner confirms no public statement implies legal approval,
      guaranteed wealth, calibrated risk, or autonomous business operation.
- [ ] Release owner records the commit SHA and immutable image digest.
- [ ] Rollback owner verifies the previous image and database backup.

## Mandatory holds

Do not publish when:

- CI is incomplete or failing;
- demo users are enabled on a public production deployment;
- placeholder secrets remain;
- the database is ephemeral without explicit acceptance;
- `/health/ready` fails;
- the audit chain is invalid;
- the public capability record overstates implemented controls;
- a critical security or privacy finding is unresolved.

## Post-publication verification

- [ ] Public console loads without external scripts, fonts, or images.
- [ ] Anonymous governance requests receive `401`.
- [ ] Direct legacy venture and agent mutations receive `409`.
- [ ] R4 requests cannot receive autonomous execution authority.
- [ ] Underclassified consequential actions are held.
- [ ] Authorization and kill-switch state are rechecked before execution records.
- [ ] Kill-switch activation blocks matching action requests.
- [ ] Rollback target remains deployable.
