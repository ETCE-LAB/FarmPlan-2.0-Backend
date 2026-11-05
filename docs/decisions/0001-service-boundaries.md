# ADR 0001: Existing service split and target rules

- Date: November 5, 2026
- Status: existing service split documented; target rules recorded, technical design open
- References: [Decision index](README.md), [Architecture and evidence](../architecture.md), [Roadmap](../roadmap.md)

## Context

The repository already has eight service directories and the shared packages `api-contracts` and `observability`. Domain runtime code currently exists for the gateway, Identity, and Farm. Compose runs Catalog, Planning, Analysis, and Media as health placeholders; the background worker is absent from Compose. The existing root README describes broader responsibilities that are not yet implemented.

This ADR documents the existing split and desired boundaries. It introduces no new service decomposition and does not declare prepared directories to be complete services.

## Documented responsibilities

| Directory | Responsibility or target responsibility |
| --- | --- |
| `services/api-gateway` | Public FastAPI boundary, authentication integration, access checks, and translation into internal calls; does not take over domain data persistence. |
| `services/identity-service` | Accounts, guest identities, login, and token/profile validation. |
| `services/farm-service` | Farm/Field and related permissions/memberships as an extension goal; own domain data and own outbox. Currently owner-filtered farm CRUD with JSONB. |
| `services/catalog-service` | Species/catalog domain, dataset tasks, and own outbox as a goal. |
| `services/planning-service` | Planning, Placement Optimizer, versioned rules, and domain-owned processing as a goal. |
| `services/analysis-service` | Soil, weather/climate, and geospatial analysis; external Soil/Weather/Geocoding/GIS adapters and GeoTIFF processing as a goal. |
| `services/media-service` | Media metadata, object-storage/CDN adapters, and domain-owned processing as a goal. |
| `services/background-worker` | Independently deployable job consumers/schedulers; outbox processing and delegation to internal domain services as a goal. |
| `packages/api-contracts` | Shared versioned interface contracts, not shared domain persistence. |
| `packages/observability` | Shared telemetry hooks, not domain orchestration. |

## Target rules

1. Domain services own their data and migrations. The currently shared PostgreSQL database configuration does not authorize cross-service domain SQL access.
2. Farm and Catalog write domain changes and outbox entries atomically in their respective local PostgreSQL transactions.
3. Workers process outbox work and invoke domain services through agreed internal contracts. Permitted outbox access must be defined separately and grants no general access to domain tables.
4. Planning, Analysis, and Media domain logic remains in those services, even when triggered asynchronously. Retries must not create uncontrolled duplicate domain effects.
5. Interface changes are versioned and tested; shared packages must not introduce hidden coupling through shared domain models or database access.
6. API and worker processing should provide correlatable logs, metrics, and traces without exposing secrets or unnecessary sensitive data.

## Consequences

Existing directory names remain unchanged. Services can be developed and operated independently, which creates explicit contract, migration, and operational work. Asynchronous results require traceable status and error handling rather than an assumption of immediate consistency. The current shared database and health placeholders do not yet fully satisfy the target rules.

## Undecided

This ADR defines neither the physical database topology nor the outbox schema, delivery mechanism/broker, event names, specific retry/idempotency techniques, or scheduling. The membership/tenant model, Redis's role, optimization algorithm, external providers, storage/CDN technology, and observability stack also remain open. These details require their own review and potentially additional ADRs; they are not invented here.
