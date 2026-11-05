# ADR 0002: Service-owned PostgreSQL and reliable asynchronous work

- Date: November 5, 2026
- Status: accepted target policy; implementation outstanding
- References: [ADR 0001](0001-service-boundaries.md), [Architecture](../architecture.md), [Roadmap](../roadmap.md)

## Context

Identity and Farm currently use PostgreSQL with shared development database credentials. Farm stores JSONB data and has no outbox. Catalog is a health placeholder; the background worker has no runtime implementation or Compose service. These facts do not establish isolation or reliable asynchronous delivery.

## Decision

- Each domain service owns its PostgreSQL data, migrations, and access permissions. No direct access to another service's domain tables or cross-service SQL joins is permitted. Logical ownership does not require separate physical database servers.
- Farm and Catalog must commit each relevant domain change and its outbox entry in the same local PostgreSQL transaction. Rollback must leave neither a partial domain change nor an orphaned event.
- Long-running analysis, imports, image processing, and optimization run in independently operated workers rather than within HTTP requests. Workers delegate domain behavior to the responsible services through agreed contracts.
- Design for at-least-once delivery, including duplicate delivery and crashes. Processing must be idempotent, retries bounded, and permanent failures visible and actionable. No exactly-once guarantee is claimed.
- Any worker permission to process a service-owned outbox must be explicitly defined and limited; it grants no general access to that service's domain tables.

## Alternatives considered

Direct database sharing would reduce initial integration work but violate ownership. Writing data and dispatching work separately would leave a failure window between the two operations. Running long work synchronously would couple request latency and availability to processing. Assuming exactly-once delivery would conceal duplicate-effect risks. None is adopted.

## Consequences

Atomic enqueueing protects the local change/event relationship, not atomicity across services or object storage. Eventual consistency, job status, duplicate suppression, recovery, and operational failure handling require explicit implementation and tests. Existing shared development credentials must not be mistaken for sufficient production isolation.

## Open questions

Physical database topology, privilege design, outbox schema, event names/versions, delivery and acknowledgment mechanism, polling or a broker, scheduling, concurrency control, idempotency technique, retry limits/backoff, and failed-work recovery remain undecided. This ADR selects no broker or worker framework.

## Verification and outstanding work

Implement service-owned migrations and least-privilege access, then test commit/rollback atomicity, duplicate processing, concurrent workers, crashes before and after effects/acknowledgment, bounded retry exhaustion, and operator-visible failures. Verify that workers cannot read arbitrary domain tables. The roadmap's Farm/Catalog outboxes and independent worker remain outstanding; this ADR supplies no runtime evidence.
