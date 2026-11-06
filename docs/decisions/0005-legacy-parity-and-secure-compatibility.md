# ADR 0005: Mandatory legacy parity with explicit, secure compatibility

- Date: November 5, 2026
- Status: accepted migration policy; capability parity unverified
- References: [Legacy feature parity inventory](../legacy-feature-parity.md), [Roadmap](../roadmap.md), [Architecture](../architecture.md)

## Context

The legacy inventory records a source-inspected baseline for the legacy backend at `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend`. Its LEG-01 through LEG-16 rows are required and parity-unverified, not evidence of a completed migration. It identifies source discrepancies, data concerns, and consumer-audit gaps. The inventory establishes a baseline, not verified implementation coverage.

## Decision

- Full functional parity is mandatory. Every legacy capability must map to an owning service, an implemented replacement, explicit data/API compatibility decisions, and concrete regression/acceptance tests. Track missing implementations and coverage; silently dropping capabilities is forbidden.
- Preserve legitimate user and operator outcomes, necessary data, and attribution rather than copying legacy technologies, accidental bugs, or vulnerabilities.
- Document intentional security/scientific corrections and their compatibility effects. Provide a secure replacement and tests; do not re-enable disabled unauthenticated mutations merely to reproduce old routes.
- Map legacy routes and operations to versioned HTTP/gRPC/job contracts, including errors, IDs, data semantics, and asynchronous behavior. Breaking client changes require an explicit adapter or coordinated consumer migration.
- Decide authorized data transfer, reconciliation, and cutover/recovery expectations before migration. Preserve required multilingual plant data and source/license evidence; English documentation does not authorize rewriting data keys or names.
- Migration completion is blocked until the inventory is verified, every capability has passing parity coverage, and compatibility/data migration decisions are explicit. Health checks, scaffolding, and one representative workflow are insufficient.

## Alternatives considered

A best-effort rewrite could silently omit capabilities. Literal bug-for-bug compatibility could preserve security defects and known scientific errors. Declaring completion from service startup would confuse infrastructure with behavior. None meets the migration requirement.

## Consequences

Migration acceptance requires capability-level evidence across domain, public API, worker, and data boundaries as applicable. Source revision pinning, approved fixtures, consumer review, and secure replacements add work but make omissions and intentional incompatibilities reviewable. Keep inventory implementation and verification statuses current as migration increments are delivered.

## Open questions

The legacy revision, actual persisted-data schemas and authorized exports, frontend/sibling-backend consumers, provider compatibility, approved scientific reference values, and concrete route/data adapters remain to be verified. The inventory's examples are not permission to select a provider or assume a reproducible raster-generation pipeline.

## Verification and outstanding work

Trace each inventory ID to implementation paths, contracts, fixtures, and named passing tests, including negative/security cases. Reconcile migrated IDs, fields, assets, checksums, and attribution; exercise recovery and consumer migration. Resolve and test the inventory's source discrepancies explicitly. Missing tests, unverified consumer behavior, or failed reconciliation block completion. This documentation performs no legacy execution, data migration, or parity testing.
