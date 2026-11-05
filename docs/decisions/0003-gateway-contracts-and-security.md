# ADR 0003: Public gateway, versioned contracts, and service security boundaries

- Date: November 5, 2026
- Status: accepted target policy; partially implemented, security hardening outstanding
- References: [ADR 0001](0001-service-boundaries.md), [Architecture](../architecture.md), [Roadmap](../roadmap.md)

## Context

The FastAPI gateway currently connects Identity and Farm, with versioned HTTP routes, bearer authentication, and module/guest checks. Identity and Farm have versioned Protobuf contracts. Farm currently enforces owner-scoped CRUD; a general membership model has not been established. Other domain services are health placeholders. Internal gRPC is currently unencrypted in local Compose.

## Decision

- Public HTTP enters through `services/api-gateway`. The gateway handles transport, authentication integration, and routing, not other services' domain persistence.
- Internal service communication uses versioned gRPC contracts maintained under `packages/api-contracts`. Contract changes require compatibility review and tests; generated artifacts must use the designated generator.
- Identity owns identity and token validation. The responsible domain service enforces permissions on its operations, including applicable guest, ownership, and farm-membership rules. Gateway checks are defense in depth, not a replacement for service authorization.
- Request-supplied roles, user IDs, and farm IDs are untrusted. A supplied identifier is not proof of authority; caller context and resource access must be validated.
- Shared contracts must not become shared persistence models. Development network isolation or unencrypted gRPC is not proof of production transport security.

## Alternatives considered

Exposing each domain directly would fragment the public boundary. Centralizing domain persistence and all authorization in the gateway would undermine service ownership and allow internal callers to bypass permissions. Unversioned interfaces would hide compatibility risks. These alternatives are rejected.

## Consequences

Services remain responsible for authorization even when the gateway already checked a request. Versioning and transport/error translation require coordinated contract tests and explicit consumer migrations. Future services must implement these boundaries rather than treating health endpoints or enabled gateway modules as completed integration.

## Open questions

The tenant/membership model, trusted caller-context propagation and validation, production service authentication and transport encryption, detailed error mappings, and compatibility/deprecation mechanisms remain to be designed. No particular identity provider, certificate system, or infrastructure product is selected.

## Verification and outstanding work

Test public HTTP-to-gRPC mappings, compatible contract evolution, invalid/expired credentials, forged caller context, unauthorized and foreign farm IDs, and guest access, including direct internal service calls. Verify least privilege and production transport protections separately. Existing owner checks do not prove membership coverage; missing domain contracts, integration, and security tests remain work under the roadmap.
