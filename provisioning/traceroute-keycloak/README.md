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

The permanent browser client is `browser-client.json`, with `browser-scope.json`
attached only to that client. It uses the exact app `/auth/callback` redirect and
S256 PKCE. Default scope is `basic`; optional scopes are `email` and
`traceroute:browser`. Browser audience is `/api/v1/`, separate from the MCP audience.
Keycloak adds server defaults to the attributes map; verify the declared keys and
exact scope memberships when comparing the returned representation.

## ChatGPT registration

`chatgpt-client.json` defines the confidential `traceroute-chatgpt` client for
ChatGPT's User-Defined OAuth Client option. Its sole redirect is the callback
shown by ChatGPT: `https://chatgpt.com/connector_platform_oauth_redirect`.
Use `client_secret_post`, request `openid` as a base scope and keep
`traceroute:owner` selected. Only `basic` is a default client scope; `email`, `offline_access`, and owner scope
are explicitly optional. ChatGPT requests email and offline refresh access during
connection. These scopes are assigned only to this client; refreshed access tokens
still require the current workspace grant on every tool call. S256 PKCE, short access tokens and separate browser
connection approval remain required. Do not enable dynamic registration or
add wildcard callbacks for this integration.

Retrieve the generated secret with the authenticated admin API and deliver it
through a private local file to the operator. Never commit the secret or include
it in console output. Read back the client settings and exact scope assignments
after provisioning. Creating this client does not grant workspace access; the
user must sign in from ChatGPT and approve the returned Traceroute consent link.

## Owner maintenance CLI

`owner-cli-client.json` is a public device-authorization client. It has no redirect
URIs, password grants, service accounts, implicit flow or authorization-code flow.
Only `basic` is default and `traceroute:owner` is optional. Its 15-minute access
token permits the separate browser workspace approval followed by owner maintenance;
the CLI discards refresh tokens and never creates its own workspace grant.

Provision this representation only in the Traceroute realm. Read back all declared
settings, the device-grant attribute and exact default/optional scope memberships.
An existing same-name client with conflicting settings must be investigated rather
than overwritten. Realm default scopes remain unchanged.

Run `traceroute-owner -operation login -owner-token-file /private/new-token`.
After browser login, `request-connection` takes that private token file and a workspace
UUID, with the existing runtime database environment. Follow the returned browser
approval link before invoking provisioning or import. Tokens must never appear in
command arguments, logs or version control.
