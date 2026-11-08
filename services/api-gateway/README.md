# Gateway authentication and error contract

Auth, user, and module JSON uses camelCase. Registration accepts `displayName`
(preferred) or the legacy `display_name` input alias. Auth returns only
`accessToken`, `tokenType`, `expiresIn`, and `user`; refresh tokens never appear
in JSON. User timestamps are UTC strings provided by Identity.

`POST /api/v1/auth/refresh` rotates the refresh credential stored in the
`refresh_token` HttpOnly, SameSite=Strict, host-only cookie, scoped to
`/api/v1/auth`. Cookies have Secure set when `APP_ENV=production` and use the
Identity-provided refresh lifetime. Auth responses are marked `Cache-Control:
no-store`. `POST /api/v1/auth/logout` revokes the presented refresh session,
returns 204, and clears the cookie after successful upstream revocation. An
absent cookie is an idempotent successful logout; upstream failures are reported
without pretending revocation succeeded. Existing access tokens expire according
to Identity policy. Guest sessions without refresh credentials clear an existing
refresh cookie rather than retaining another account's session.

## CSRF and deployment policy

All auth POST routes, including login/registration/guest routes which can replace
a cookie, reject `Sec-Fetch-Site: cross-site`. If Origin is present, it must match
the request's public scheme and authority exactly; null, malformed, and foreign
origins are rejected. Requests without Origin are accepted for non-browser clients
unless fetch metadata reports cross-site. This relies on browsers supplying Origin
or fetch metadata for cross-site POST requests and complements SameSite=Strict;
there is no cross-origin credentialed browser flow. Trusted reverse-proxy handling
must preserve the actual public scheme/host and restrict trusted forwarded headers;
do not blindly trust client-supplied forwarding headers. Explicit default ports
are currently compared literally, so clients should use the canonical public URL.

Profile/password/delete routes use bearer authorization only, not the refresh
cookie. Identity owns account and guest authorization. Profile PATCH currently
supports only a nonblank `displayName`. Password changes and account deletion
return an empty 204. Settings are not implemented because no Identity RPC exists.

## Errors and compatibility

All HTTP, request-validation, gRPC, and unexpected application errors use
`{ error: { code, message, details: [{ path, code, message }] } }`.
Messages are deliberately generic and never forward upstream details or submitted
validation values. Validation paths identify the input location; detail codes are
Pydantic validation types. Stable top-level codes and response schemas are exposed
through OpenAPI in development/test. Production documentation remains disabled.
Farm responses now use typed direct resources and paginated `items`, with GET,
PATCH, and DELETE 204. Their errors use this global envelope. See the
[Farm guide](../farm-service/README.md) for legacy adapters, mock mode, and
unimplemented geometry/Planning capabilities. Consumers must migrate snake_case auth/user/module response reads and
legacy `detail` error reads. These are intentional API compatibility changes.

Gateway tests mock gRPC. They do not establish real Identity/database behavior,
refresh concurrency/replay guarantees, browser/proxy acceptance, or legacy parity.
Bruno session requests require its cookie jar enabled; account deletion and password
changes are explicit, destructive requests and should use disposable test accounts.
Set the Bruno `new_password` environment value before running the password request;
after success, update `registered_password` before another login. Refresh stores the
new access token as `user_token`; do not run it against the guest session cookie jar.
