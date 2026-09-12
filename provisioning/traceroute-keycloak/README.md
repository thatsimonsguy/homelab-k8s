# Traceroute owner-token configuration

These explicit Keycloak Admin API representations target only the `traceroute`
realm. They are provisioning inputs, outside Argo's workload templates; do not
import them into another realm or change realm-wide default scopes.

- `owner-scope.json`: optional `traceroute:owner` scope with the fixed access-token
  audience `https://app.traceroutehealth.com/mcp`. The mapper excludes ID tokens.
  Scope consent describes full owner management; an approved application connection
  grant remains separately required by the hub.
- `token-check-client.json`: temporary public authorization-code client with one
  exact loopback redirect, S256 PKCE and consent. It has only `basic` as a default
  scope and `traceroute:owner` as an optional scope. No password, implicit, service
  account or offline-access flow is enabled.

Create the scope through `POST /admin/realms/traceroute/client-scopes`. Inspect an
existing same-name scope before changing it. Create the test client through
`POST /admin/realms/traceroute/clients`, then read back the client, mappings and scope
assignments. Keep owner scope out of both realm-wide default scope lists.
Future approved MCP clients must be explicitly assigned the optional owner scope
and request `openid traceroute:owner`; do not relax audience checks for compatibility.

## Real-token check

Use a temporary loopback receiver at `http://127.0.0.1:8765/callback`. Generate fresh
state, nonce and PKCE verifier; request an authorization code with S256 and the owner
scope. Use social login and consent, never a password grant or impersonation.

Exchange the code, refresh once, then send both access tokens through the hub's
`internal/authn` verifier with the canonical issuer, MCP audience and owner scope.
Assert that verified issuer, subject, authorized client (`azp`) and session (`sid`)
remain identical across refresh. Independently validate the ID-token signature,
client audience and nonce, and prove that the ID token is rejected as API authority.
Log out with the refreshed refresh token and assert subsequent refresh returns
`invalid_grant`. Keep credentials and token responses in memory; report booleans only.

Remove the temporary client after success or expiration of the test window. Retain
the reusable owner scope. A failed test must not be worked around by dropping scope,
audience, token-type or session checks. This probe creates no hub account, workspace
or connection grant and writes no health data. It does not establish full MCP-client
compatibility, application onboarding or deployment readiness.
