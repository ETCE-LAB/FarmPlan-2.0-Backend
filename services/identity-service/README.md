# Identity account lifecycle

Apply migrations in filename order, including `002_identity_sessions.sql`, before running the updated service. Existing users receive credential version zero and an updated timestamp at migration time; their original creation timestamps remain intact. Existing versionless access tokens remain valid against version zero until expiry or a password change.

Registration and login return the original auth fields plus a complete profile, access lifetime, and a random 30-day refresh token. Only SHA-256 refresh-token digests are persisted. Refresh atomically consumes the old token and creates a replacement. Reuse is rejected; it does not revoke the replacement session. The gateway must keep refresh tokens out of JSON/logs and use a secure HttpOnly cookie with appropriate SameSite/CSRF protection. Guests remain account-free, expire after 24 hours, and cannot refresh or mutate accounts.

Logout idempotently deletes the supplied refresh token. It does not invalidate already-issued access tokens; they expire within one hour. Password change requires the current password, increments the credential version, and deletes all refresh sessions in the same transaction. `GetUser` checks current persisted credentials, so password changes and self-deletion invalidate old access tokens. Consumers must validate through Identity rather than accepting a signature alone.

Profile updates support optional display-name presence; omitted means unchanged and blank is invalid. Self-deletion deletes only Identity-owned data and refresh sessions through the foreign-key cascade. It does not cascade into Farm or other services. Cross-service retention/cleanup is not implemented. Optional language/theme/base-layer settings are deferred.

Timestamps are ISO 8601 UTC strings. No existing RPC or field number was removed. Expired refresh records are rejected but require an operational cleanup policy; no cleanup worker is implemented.

Tests use an in-memory SQL test double, not PostgreSQL. They cover lifecycle behavior, but do not establish migration execution, transaction rollback, concurrent rotation, or database locking correctness. Real PostgreSQL and gateway integration checks remain required.

AI-assisted implementation and tests: OpenAI GPT-6.1-Sol. Repository-wide documentation and provenance updates are delegated to the coordinating parent because this increment owns only Identity files and its protobuf.
