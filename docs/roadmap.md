# Roadmap

[Index](README.md) · [Target architecture](architecture.md) · [Legacy feature parity](legacy-feature-parity.md)

All items are open work, not claims of delivered capabilities. P0 precedes P1, which precedes P2; independent work within a priority may proceed in parallel. All maintained and new documentation, agent instructions, and skills must be in clear English.

## Mandatory legacy parity and migration completion gate

Full functional parity with `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend` is mandatory. No legacy capability may be silently dropped. [The parity inventory](legacy-feature-parity.md) is a source-inspected baseline; consumer coverage and implementation parity still require verification.

Before migration can be declared complete, the feature inventory must be verified against the legacy implementation, every capability must have an owning service and regression/acceptance tests, data and API compatibility decisions must be explicit, and parity tests must pass. Insecure legacy behavior must not be copied blindly: record security corrections, compatibility impacts, and tests for the secure replacement rather than silently removing the capability.

## Delivered increments with remaining verification

- Identity wishlist increment: camelCase Auth/User/Module HTTP contracts, consistent gateway errors, refresh/logout, profile PATCH, password change, and Identity-only account deletion are implemented with unit/mock tests. See the [Gateway](../services/api-gateway/README.md) and [Identity](../services/identity-service/README.md) policies. PostgreSQL migration/concurrency validation, live gRPC acceptance, optional settings, expired-session cleanup, and cross-service account-deletion retention/cleanup remain open. This does not establish legacy parity or complete the domain wishlist.

## P0 – Boundaries and a reliable foundation

- [ ] **Enforce the contribution and release workflow.** Acceptance: [CONTRIBUTING.md](../CONTRIBUTING.md) is enforced by protected `develop` and `main`, reviewed feature-branch PRs only into `develop`, and separate reviewed `develop` → `main` promotion PRs; all tests and required checks pass on feature PRs, the current integrated `develop`, promotion PRs, and merged `main`, with integration/acceptance validation before promotion; Conventional Commits and AI disclosure/model/co-author trailers are validated and preserved on squash. Configure semantic-release in trusted CI to create version tags and release notes only after passing checks on `main`, with no release-bot commits pushed directly to `main`. Test version selection, breaking changes, permissions, and release concurrency. Policy documentation alone does not establish enforcement.

- [ ] **Verify the legacy feature inventory.** Acceptance: inspect the legacy implementation and verify coverage in the parity inventory, including APIs, domain workflows, background work, integrations, permissions, and data behavior. Map every capability to an owning service and named regression/acceptance tests; track gaps explicitly. Directory scaffolding and health checks do not establish parity.
- [ ] **Decide data and API compatibility.** Acceptance: document legacy-to-target mappings, request/response and error behavior, authentication/authorization changes, stored-data transformations, and migration/rollback or recovery expectations. Record intentional incompatibilities and security corrections with rationale and acceptance tests; no capability is silently dropped.
- [ ] **Specify domain contracts and data ownership.** Acceptance: versioned API/event contracts for the next increment are reviewed; Farm/Field, Catalog, and permissions have documented owners and error cases. Open decisions are explicitly recorded rather than implicitly imposed.
- [ ] **Secure service-owned persistence.** Acceptance: versioned migrations and defined DB privileges prevent unintended cross-service access; the shared local Compose database is documented as a development simplification. Migration and rollback/recovery checks are traceable.
- [ ] **Extend Farm/Field and Catalog domain functionality.** Acceptance: required CRUD/permission cases run through real services rather than health placeholders; positive cases, validation, and unauthorized access are tested. Decide the Field model before migrating it out of JSONB.
- [ ] **Implement transactional outboxes in Farm and Catalog.** Acceptance: domain changes and outbox entries commit atomically; commit, rollback, and retry tests demonstrate that no inconsistent intermediate state is created. Document the schema and delivery contract.

## P1 – Asynchronous domain processes

- [ ] **Run the worker as an independent process.** Acceptance: startup/shutdown behavior and deployment are available; both outboxes are processed according to the agreed contract. Test concurrency, recovery after crashes, duplicate delivery, and permanent failures; status and errors are discoverable.
- [ ] **Connect Planning and the Placement Optimizer.** Acceptance: a representative job produces a traceable, persisted result; input/rule versions and error cases are traceable; duplicate delivery creates no duplicate domain effects.
- [ ] **Implement Analysis with external adapters and GeoTIFF Storage.** Acceptance: Soil/Weather/Geocoding/GIS contracts and provider requirements are clarified; timeouts, rate limits, outages, and retries are tested. Analysis metadata and GeoTIFF references remain consistent; credentials are configured externally.
- [ ] **Implement Media with object storage/CDN.** Acceptance: authorized object access and metadata persistence work; failed uploads, retries, and orphaned objects have demonstrated handling. Document providers and access/deletion rules.
- [ ] **Define Redis's role and integrate it selectively.** Acceptance: a justified use case with expiration/invalidation and failure behavior is documented and tested; Redis is not a second source of domain truth.
- [ ] **Implement capability-level parity tests.** Acceptance: each inventoried legacy capability has executable regression/acceptance coverage in its owning service and, where appropriate, at the public API or workflow boundary. Verify compatibility decisions and secure replacements with representative legacy fixtures; report missing coverage and failures explicitly.

## P2 – Operations and end-to-end acceptance

- [ ] **Integrate API and worker observability.** Acceptance: an API request can be correlated through to the worker result; errors, latency, and outbox backlog are visible. Example alerts and a troubleshooting guide exist; telemetry contains no tokens or secrets.
- [ ] **Verify production hardening and recovery.** Acceptance: secrets, internal transport security, least privilege, external data sharing, backup/restore, and retention are decided and checked; development defaults are not used in production.
- [ ] **Accept a reproducible complete workflow.** Acceptance: a documented run from a Farm/Catalog change through outbox/worker to a Planning, Analysis, or Media result works, including a simulated failure. CI checks contracts and relevant tests; development documentation matches the actual workflow.
- [ ] **Verify full legacy parity before migration completion.** Acceptance: reconcile the verified inventory with implementation and passing regression/acceptance results for every capability and owner. Review data/API compatibility decisions and test data migration and secure replacements. Unresolved capability gaps, unverified inventory entries, or failing/missing parity tests block completion; health checks and the representative workflow alone are insufficient.
