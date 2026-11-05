---
name: legacy-migration
description: Audit FarmPlan legacy capabilities and map data, APIs, consumers, secure corrections, and parity fixtures for a bounded migration increment.
---

# Legacy migration

## Scope and preparation

Use for source audits, compatibility decisions, fixture preparation, and cutover evidence, not general feature implementation. Paths below are repository-root-relative unless stated otherwise. Read `docs/README.md`, `CONTRIBUTING.md`, `docs/architecture.md`, `docs/roadmap.md`, and `docs/legacy-feature-parity.md`. The inventory is a source-inspected baseline with unverified parity, not proof of implementation. Keep the affected inventory entries current when a requested migration increment changes their implementation or verification status; never mark unverified parity as complete.

Audit the legacy source read-only at `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend`. This local reference is not a portable dependency. Record the source revision using available authorized evidence; do not execute legacy code, query production data, or invoke providers merely to inspect behavior. If evidence is unavailable, report the gap rather than inventing it.

## Workflow

1. Select a bounded set of inventory IDs, such as LEG-03/04 for import normalization. Record source file/symbol evidence, effective definitions, actual route registration, consumers, and disabled operations. Separate frontend and sibling `backend-next/` claims from observed Flask behavior.
2. Map each capability to Identity, Farm/Field, Catalog, Planning, Analysis, or Media; identify concrete implementation paths under `services/`, gateway routes in `services/api-gateway`, contracts under `packages/api-contracts`, and named regression/acceptance tests. Track missing implementation and coverage explicitly; scaffolding is not parity.
3. Specify old-to-new request, response, status/error, authentication, permission, pagination, normalization, and synchronous-to-job mappings. Choose an explicit compatibility adapter or coordinated consumer migration for breaking changes.
4. For approved exports, map IDs, nested fields, numeric/null semantics, duplicates, raw plant values, source versions, checksums, and image/species references into service-owned PostgreSQL models and object references. Preserve multilingual names and required data keys. Define reconciliation counts, field-level checks, recovery, and cutover criteria before moving data; no destructive replacement without explicit approval.
5. Build approved, versioned, sanitized fixtures in the affected service's existing test layout. Pin source provenance and expected results; never include credentials or personal farm payloads. Cover normal, empty, malformed, boundary, and permission cases. Do not introduce MongoDB or new dependencies just to emulate legacy internals.
6. Record intentional corrections with rationale, compatibility impact, preserved user outcome, and negative/security tests. Examples include exposed server paths, arbitrary raw columns, destructive import defaults, image redirect SSRF, and erroneous hardiness temperature signs. Resolve scientific expectations against an approved reference, not a known bug.
7. Delegate implementation to `../backend-feature/SKILL.md`, persistence/recovery to `../database-outbox/SKILL.md`, raster/provider work to `../geospatial-analysis/SKILL.md`, and images to `../media-pipeline/SKILL.md`. Do not duplicate those implementation procedures here.

## Acceptance checklist

- [ ] Every selected capability has source evidence, owner, API/data mapping, concrete tests, and an explicit gap status.
- [ ] Approved fixtures test compatibility and secure replacements; actual consumers and stored schemas are verified or marked unresolved.
- [ ] Reconciliation, recovery, licensing, and authorized asset transfer are documented for the increment.
- [ ] `../backend-validation/SKILL.md` is followed; exact executed checks and missing integration coverage are reported. Mocks alone do not prove data/provider parity.
- [ ] Full migration completion is not claimed until every inventory capability is verified, compatibility decisions are explicit, and all required parity tests pass. Never silently reduce scope.
