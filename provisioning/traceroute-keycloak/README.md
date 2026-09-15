# Traceroute owner-token configuration

These explicit Keycloak Admin API representations target only the `traceroute`
realm. They are provisioning inputs, outside Argo's workload templates; do not
import them into another realm. Dynamic registration narrows defaults for future clients as described below.

- `owner-scope.json`: optional `traceroute:owner` scope with the fixed access-token
  audience `https://app.traceroutehealth.com/mcp`. The mapper excludes ID tokens.
  Scope consent describes full owner management. Hosted OAuth sign-in establishes the
  default connection automatically; legacy maintenance clients retain explicit approval.
- `token-check-client.json`: temporary public authorization-code client with one
  exact loopback redirect, S256 PKCE and consent. It has only `basic` as a default
  scope and `traceroute:owner` as an optional scope. No password, implicit, service
  account or offline-access flow is enabled.

Create the scope through `POST /admin/realms/traceroute/client-scopes`. Inspect an
existing same-name scope before changing it. Create the test client through
`POST /admin/realms/traceroute/clients`, then read back the client, mappings and scope
assignments. Owner scope is never a default token permission; it is optional for hosted dynamic registrations.
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
still require the current workspace grant on every tool call. S256 PKCE, short-lived
access tokens and OAuth consent remain required. ChatGPT needs no second application
approval. Dynamic registrations use the constrained policy below; wildcard callbacks remain forbidden.

Retrieve the generated secret with the authenticated admin API and deliver it
through a private local file to the operator. Never commit the secret or include
it in console output. Read back the client settings and exact scope assignments
after provisioning. Creating this client does not grant workspace access; the
user signs in from ChatGPT and grants the owner scope. The first workspace tool call
binds that verified session to the default workspace; no UUID or second link is needed.

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

## Claude hosted registration

`claude-client.json` registers `traceroute-claude` independently from ChatGPT.
The exact hosted callback is `https://claude.ai/api/mcp/auth_callback`; no loopback
or wildcard redirects are permitted. Require S256, explicit full-owner consent,
and confidential client authentication. Only `basic` is default; email, owner and
offline refresh scopes are optional. Verify these settings and scope assignments
after provisioning; preserve an existing secret on retries.

For the optional fixed-client fallback, use `https://app.traceroutehealth.com/mcp`,
client ID `traceroute-claude`, and the secret delivered in a private local file.
Sign-in automatically selects the user's default workspace; no additional approval
link is required. Claude Code is a separate future integration. Callback and setup
requirements: https://claude.com/docs/connectors/building/authentication .

## Hosted dynamic registration

Claude can use the MCP server URL alone with its optional client credentials blank.
`configure-dcr.py` applies `dynamic-registration.json` and `connect-scope.json` using
cluster operator access (`kubectl` for the existing Keycloak admin secret). Run it
on the cluster host with the adjacent JSON files; it preserves existing client
secrets, assignments and unrelated client policies. Read back settings and run
`verify-dcr.py` after changes (it removes its disposable registrations). No application admin credentials are deployed.

Anonymous DCR and registration-token updates are constrained to HTTPS callbacks on
exact hosts `claude.ai` and `chatgpt.com`, without wildcards, fragments or loopback.
The policy does not authenticate the caller as Anthropic/OpenAI; consent and PKCE
remain mandatory, and authorization returns only to a permitted registered URI.
Source-IP filtering is disabled because requests traverse the shared tunnel proxy.
PKCE S256, consent, and disabled full-scope, password and implicit grants are enforced.
Caller-supplied protocol mappers and browser scope are forbidden. The realm's 200-client
cap bounds registrations; remove abandoned registrations through operator tooling if
it is reached. Claude Code loopback registrations remain outside this integration.

New clients get only `basic` by default; optional scopes are email, offline refresh,
owner and connect. Existing client scope assignments are preserved. The empty `openid`
marker accommodates Keycloak 26.3 DCR scope validation. `traceroute:connect` expresses
consent to automatic account linking; the API requires a verified owner token as well.
The realm rotates refresh tokens with zero reuse, including public clients. Clients
must retain the newly returned refresh token. Fixed hosted registrations remain valid.

Registration does not provision a user or grant access. Social sign-in, invitation
eligibility and OAuth consent still apply. Dynamic IDs need no application allowlist;
verified issuer/subject identify the account, and client/session identify its connection.

## Social identity providers

The realm's `google` and `microsoft` identity providers exist only in Keycloak; no
representation lives in this repository. Both use the `traceroute-first-broker` flow, whose
single step is Create User If Unique, so a social login never links to an existing user by
matching email (ADR-0016). A future email-confirmed linking step needs realm SMTP; Keycloak
skips that step silently when SMTP is unconfigured.

Trust Email is on for `google` (2026-09-14). Google is an OIDC provider, so Keycloak copies
Google's own `email_verified` claim and an exact verified invitation match approves without
an operator. Trust Email stays off for `microsoft` (tenant `common`): its provider takes the
Graph `mail` or `userPrincipalName`, which a work tenant's admin controls, and would mark every
such address verified. Microsoft claims go to approval (ADR-0017 amendment, 2026-09-14).
Change a provider by reading its representation and writing it back whole; Keycloak keeps
the stored client secret when the masked `**********` value is written back.
