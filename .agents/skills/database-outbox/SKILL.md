---
name: database-outbox
description: Work on FarmPlan PostgreSQL migrations, transactional outbox events, and idempotent workers with bounded retries.
---

# Database, outbox, and workers

Read `AGENTS.md`, `docs/architecture.md`, `docs/development.md`, and existing migrations and repository transactions in the affected service. First check which outbox components actually exist.

Consult [the legacy feature parity inventory](../../../docs/legacy-feature-parity.md), a source-inspected baseline whose parity remains unverified. Full functional parity with `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend` is mandatory; do not silently drop legacy data behavior or background capabilities. Map each to an owning service and regression/acceptance tests. Document data/API compatibility and migration/recovery decisions, test data transformations, and replace insecure behavior securely rather than copying it blindly. Inventory verification and passing parity tests are required before migration completion. Maintain all documentation, agent instructions, and skills, including new documentation, in clear English.

## Workflow

1. Identify table ownership and the transaction boundary. Do not read or write other services' tables; even a shared PostgreSQL server does not change this boundary.
2. Add versioned migrations following the existing pattern. Check existing data, constraints, indexes, and rollout compatibility. Obtain explicit approval before destructive changes.
3. When a domain event is required, store the domain change and outbox entry atomically in the same database transaction. Separate, subsequent event persistence is not a substitute.
4. Define the event ID, type, schema version, and a minimal payload without unnecessary personal data. Document new contracts explicitly.
5. Plan claiming/leases for concurrent workers, recovery after crashes, and idempotent domain processing. Assume at-least-once delivery.
6. Bound attempts and backoff; define a state for permanently failed jobs and safe manual resumption. Keep external calls out of long database transactions.
7. A generic worker invokes other domains through gRPC, not their tables. A service-owned outbox processor may manage its own tables.

## Checks

Test atomic rollback, duplicate delivery, concurrent processing, process termination/recovery, and exhausted retries. Distinguish real PostgreSQL integration tests from mocks. Use `../backend-validation/SKILL.md`; document database checks not run and open operational decisions.
