---
name: media-pipeline
description: Design or implement FarmPlan asynchronous image ingestion with attribution, SSRF-safe bounded fetching, and consistent object-storage metadata.
---

# Media pipeline

## Scope and preparation

Use for image ingestion, curated metadata, caching, authorized access, and storage failure handling. Read `docs/architecture.md`, `docs/roadmap.md`, `CONTRIBUTING.md`, and LEG-11 through LEG-15 in `docs/legacy-feature-parity.md`. Paths here are repository-root-relative. Inspect `services/media-service`, `services/background-worker`, `services/api-gateway`, and `packages/api-contracts` before choosing an increment. The documented Media service is a health placeholder; object/CDN adapters and workers are targets, not established implementations. Do not select a provider or add dependencies without a concrete need.

## Workflow

1. Keep images, attribution, and object metadata owned by `services/media-service`. Keep HTTP transport in `services/api-gateway` and version internal contracts under `packages/api-contracts`. Resolve Catalog linkage through contracts, never cross-service SQL.
2. Define authorized read, upsert, import/seed, and deletion rules, including guest and foreign-resource cases. Preserve source-ID lookup normalization, pending-image/list behavior, and explicit API compatibility decisions. Never restore public legacy mutations or automatic startup seeding.
3. Preserve image URL, source-page URL, source/catalog ID, author and author URL, license name and URL, access date, source version, and checksum where applicable. Verify redistribution terms before copying assets; do not infer a license from a host name. Retain attribution through transformations and delivery.
4. Fetch and transform images asynchronously through domain-owned jobs. Define status, cancellation where required, bounded attempts/backoff, terminal errors, and idempotency. Use `../database-outbox/SKILL.md` for transactional scheduling and crash recovery rather than inventing a separate delivery system.
5. Before every outbound request, validate HTTPS scheme, approved exact hosts/ports, and resolved addresses; reject credentials in URLs and loopback, private, link-local, reserved, and internal destinations, including IPv6. Prevent DNS rebinding by ensuring the connection uses a validated destination while preserving TLS hostname verification. Disable automatic redirects; validate each redirect target and cap hops before requesting it. Never forward credentials across redirects. If the client cannot enforce these properties, block fetching until a safe approach is agreed.
6. Set connect/read/total deadlines, streaming transfer and decoded-image size limits, supported MIME/signature checks, pixel/dimension limits, and bounded concurrency. LEG-14 records a 20 MiB transfer cap and 20-second timeout: preserve these bounds or document and test an explicit compatibility decision. Treat filenames and source IDs as untrusted; generate safe object keys. Do not log signed URLs or complete external payloads.
7. Define URL/version-aware cache keys and cache-hit behavior. Keep binaries in object storage and authoritative metadata in service-owned PostgreSQL, not Redis or local permanent paths. No cross-system atomicity is assumed: stage uploads, verify content, publish metadata only when usable, and define idempotent compensation/reconciliation for failed metadata commits, orphaned objects, concurrent writes, interrupted uploads, and deletes. Cleanup must not remove referenced/shared objects; destructive cleanup needs explicit approval.

## Acceptance checklist

- [ ] Fixtures cover attribution, pending/null/empty URLs, normalized IDs, unknown IDs, and unauthorized mutations.
- [ ] Mocked fetch tests cover forbidden addresses, rebinding protection, redirect escape/loops, oversized/chunked content, MIME mismatch, decompression limits, timeouts, and temporary-resource cleanup; no live provider calls by default.
- [ ] Job tests cover cache hits, URL changes, duplicates, concurrent writes, retry exhaustion, and crashes between object and metadata operations.
- [ ] Authorized delivery and object/metadata consistency are checked against real storage integration when available; mock coverage is labeled honestly.
- [ ] Finish with `../backend-validation/SKILL.md`; report provider/access/deletion decisions still open and do not claim the pipeline exists from directory structure alone.
