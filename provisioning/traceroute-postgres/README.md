# Traceroute trial database

Use dedicated database `traceroute_trial` on the existing Postgres 16 service.
`traceroute_owner` owns the database/schema; `traceroute_runtime` is the restricted
application login. Both are non-superusers without role/database creation,
replication or RLS bypass. PUBLIC has no database access. The runtime role has
CONNECT plus only the privileges granted by `postgres.Migrate`.

The migration SealedSecret is operator-only and intentionally outside the Argo
application. Apply it in namespace `traceroute`, wait for unsealing, then apply the
versioned migration Job. Require Job completion before deploying the matching
product image. Delete the migration Job, Secret and SealedSecret after completion;
retain this encrypted recovery source. Never add this credential to the runtime
Deployment. Repeatable migrations do not seed users or health data.

The runtime SealedSecret lives in `apps/traceroute/templates`. The product uses a
single replica and Recreate because browser sessions live in process memory.
TLS terminates at Cloudflare; the database connection stays within the cluster.

Owner invitations are issued by `traceroute-admin -operation invite -email EMAIL
-invitation-file FILE` using operator credentials. Copy the token into an
`https://app.traceroutehealth.com/onboarding#token=TOKEN` link and deliver it manually.
Do not put invocation output into pod logs or commit the invitation file. The
nightly backup and restore rehearsal requirements remain ADR-0006/0022 in the
application repository; finish them before inviting trial participants.
