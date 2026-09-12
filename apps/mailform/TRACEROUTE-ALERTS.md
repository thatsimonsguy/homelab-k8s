# Traceroute trial operational email

Use `POST http://mailform.mailform.svc.cluster.local:3000/traceroute-alerts`
from the cluster, with `Authorization: Bearer <token>` and URL-encoded form fields
`subject` and `body`. The body is HTML: escape variable text. Do not send attachments,
health observations, credentials, invitation links, or raw exception payloads.

The endpoint and bearer token are stored in Secret `mailform/traceroute-alert-client`,
keys `endpoint` and `bearer-token`. Deliver only these keys to a future caller's
namespace through the sealed-secret process; never give the caller the SMTP target
configuration. SMTP credentials remain in `mailform-traceroute-targets`.

The target fixes the recipient to Matt's personal inbox, reuses the existing contact
sender and SMTP transport, and prefixes subjects with `[Traceroute trial]`.
There is no public ingress for `/traceroute-alerts`. Do not add one.

Use concise event type, UTC timestamp, job/run ID, environment, and a sanitized error
summary. For a setup test, explicitly say that it is a delivery test, not a real
backup/purge/journal failure.

The relay returns 200 after SMTP acceptance, not confirmed inbox delivery. Other
responses include 401 for authentication, 422 for invalid fields, 429 for rate
limiting, and 500 for parsing or SMTP failures. Use URL-encoded forms, not JSON:
the deployed relay's global JSON parser consumes JSON before its form parser.

The target limits each source IP to 10 requests per 300 seconds, in memory. The
caller must handle retry/backoff, deduplication and alert grouping; this relay has no
durable queue. SMTP timeouts can have ambiguous delivery, so retries may duplicate
messages. These caller behaviors require implementation and tests.

Target configuration is loaded at process startup. After changing target secrets,
restart Mailform through a GitOps pod-template change. Rotate the target's `key`
and the client's `bearer-token` together.

Cluster-hosted email cannot report a full cluster outage. Matt's existing Cloudflare
tunnel-down email is the separate signal for loss of tunnel connectivity; it does
not prove that individual jobs or services are healthy.
