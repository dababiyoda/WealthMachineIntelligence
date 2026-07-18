# Governed Preview Deployment

## Release classification

Deploy this artifact only as a controlled preview. It is suitable for reviewing
the operator experience and exercising local governance records. It is not a
production autonomous venture operator.

## Required secrets and configuration

Set all values in `.env.example`. At minimum:

- a persistent `DATABASE_URL`;
- a random `JWT_SECRET_KEY` containing at least 32 characters;
- a unique operator username and password stored in the deployment secret
  manager;
- exact trusted hosts and allowed origins;
- an independent DALEOBANKS intake token if that bridge is enabled.

Production startup fails when the database or JWT secret is missing. Production
intake fails closed when its token is missing. Built-in demo identities are off
by default.

The current browser session uses a bearer token in session storage. Treat the
deployment as a controlled review surface, do not add third-party scripts, and
do not expose regulated or restricted data through this preview identity flow.

The `0.2.0-rc1` image includes the SQLite driver used by the bounded preview.
It does not bundle a PostgreSQL driver or claim production database maturity.
Do not change database engines without adding the driver, versioned migrations,
backup/restore evidence, and a reviewed deployment profile.

## Publication procedure

1. Review `spec/uat/v1/current-capability.json` and confirm the public claim
   boundary is still accurate.
2. Complete `RELEASE_CHECKLIST.md` with named human owners.
3. Require green GitHub test and container-smoke jobs for the exact commit.
4. Trigger `Publish governed preview image` manually.
5. Type `PUBLISH_GOVERNED_PREVIEW` when the workflow requests authorization.
6. Deploy the immutable `sha-<commit>` image, not a floating tag.
7. Verify `/health/live`, `/health/ready`, `/api/v1/system/capabilities`, and the
   operator console from outside the deployment network.
8. Record the deployment commit, image digest, operator, time, and rollback
   target.

## Rollback

Keep the previous immutable image digest. If readiness fails, authentication
behaves unexpectedly, the capability disclosure is wrong, or the audit chain
is invalid:

1. stop traffic;
2. preserve logs and database state;
3. redeploy the previous image digest;
4. verify readiness and authentication;
5. open an incident record before resuming evaluation.

The preview does not yet claim tested database point-in-time recovery. Back up
the database before every deployment and test restoration before relying on it.
