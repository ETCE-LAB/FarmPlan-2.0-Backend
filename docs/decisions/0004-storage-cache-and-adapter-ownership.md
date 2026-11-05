# ADR 0004: Binary storage, non-authoritative Redis, and domain adapters

- Date: November 5, 2026
- Status: accepted target policy; storage and adapter implementation outstanding
- References: [ADR 0001](0001-service-boundaries.md), [Architecture](../architecture.md), [Roadmap](../roadmap.md), [Legacy parity](../legacy-feature-parity.md)

## Context

Redis runs in Compose but is not integrated into the reviewed domain paths. Analysis, Planning, and Media remain health placeholders. There are no implemented external analysis, GeoTIFF, object-storage, or CDN adapters. Legacy capabilities include raster analysis, media metadata/cache behavior, and integrations requiring a consumer audit.

## Decision

- PostgreSQL holds service-owned authoritative domain data and metadata. Binary media and GeoTIFFs belong in object storage, referenced through metadata owned by the responsible service.
- Redis is limited to justified cache or temporary-state use. It replaces neither authoritative PostgreSQL data nor the transactional outbox. Expiration, invalidation, and failure behavior must be defined before adopting a use case.
- Analysis owns Soil/Weather/Geocoding/GIS adapters, analysis, and GeoTIFF processing. Planning owns placement optimization and its rules. Media owns media metadata and object-storage/CDN adapters. Shared storage infrastructure does not transfer domain ownership.
- The gateway and generic worker do not absorb these domain adapters or algorithms. Long-running work follows [ADR 0002](0002-persistence-and-reliable-workers.md).
- External calls require timeouts, bounded retries, understandable errors, and quota/cost/privacy controls. Geospatial contracts must explicitly state CRS, coordinate order, units, and raster resolution. Object access must be authorized; provider credentials belong in external configuration, not source or logs.

## Alternatives considered

Using Redis as the system of record would violate the persistence boundary. Storing binaries in domain rows or relying on a worker's local filesystem as the authoritative target would conflate metadata persistence with binary lifecycle. Centralizing adapters in the gateway or worker would obscure domain responsibility. These alternatives are not adopted.

## Consequences

Metadata and objects require coordinated lifecycle and recovery handling, not an assumed cross-store transaction. Cache loss must not lose authoritative domain data. Authorized access, failed uploads, orphan cleanup, retention/deletion, attribution, and provider outages need explicit designs and tests. Legacy local cache paths and provider mentions do not select target infrastructure.

## Open questions

Object-storage/CDN products, external providers and credentials, deployment topology, object naming/access mechanisms, retention and cleanup, Redis use cases and expiration policies, and specific optimization rules remain unresolved. No provider, cache strategy, or geospatial conversion is implicitly selected here.

## Verification and outstanding work

Test metadata/object consistency under failed and repeated work, authorized reads/deletes, interrupted uploads/downloads, orphan handling, cache eviction/outage, and bounded provider failures using mocks by default. Test geospatial axis/CRS/unit/resolution boundaries and legacy raster fixtures. Verify provider terms, attribution, privacy, and real integrations separately before claiming readiness; no paid or live provider call is authorized by this ADR.
