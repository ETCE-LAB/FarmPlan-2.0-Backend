# Farm and Field service

Owner-scoped Farm and independent Field CRUD are exposed through the gateway and generated Farm v1 gRPC contracts. PostgreSQL remains the default; no database server, worker, outbox, or Planning implementation is added.

## Development JSON adapter

Set `FARM_STORAGE_BACKEND=json` and `APP_ENV=development` explicitly:

```sh
APP_ENV=development FARM_STORAGE_BACKEND=json docker compose -f infra/compose.yaml up --build -d farm-service api-gateway
```

Compose still starts its existing PostgreSQL/migration dependencies; Identity requires PostgreSQL. JSON mode loads `src/farmplan_farm/seed.json` into process-local memory. Writes never modify the seed. Restart resets all changes; replicas have independent state. Non-development environments reject JSON mode. Normal operation defaults to `postgres` and requires `DATABASE_URL`.

The synthetic Farm `c56c779b-2ee1-4a15-af56-7a3c1c4fb3c8` and its synthetic Field belong exclusively to owner `9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4`. They create no Identity account or token. Foreign users cannot read them, including through the Field UUID; their own Farm lists remain empty until they create resources. Guests are denied by the gateway even if module flags enable Farms.

## Farm HTTP contract

All routes are under `/api/v1` and use direct camelCase resources, UUID identifiers, service-owned ISO 8601 UTC timestamps, and the shared error envelope.

- `GET /farms?page=1&pageSize=20`: `{items,total,page,pageSize}`, newest first with UUID tie-breaking. Page size 1–100; out-of-range pages are empty.
- `POST /farms`: 201 Farm. Supports `name`, `location`, `climateZone`, `boundary: Polygon|null`, `notes`, and owner-only `contact: {ownerName,email}|null`. Legacy create payloads remain accepted.
- `GET /farms/{id}`, `PATCH /farms/{id}`: direct Farm. PATCH preserves omitted properties; null boundary/contact clears them. Boundary changes must still cover every independent Field and are rejected atomically otherwise.
- Deprecated partial `PUT /farms/{id}` preserves legacy embedded `fields` and `template` internally; caller `createdAt` is ignored. No automatic migration, coordinate conversion, ID assignment, or unit guessing is performed for embedded data.
- `DELETE /farms/{id}`: empty 204, removes independent Fields as well as embedded JSON. PostgreSQL uses an FK cascade. **Plans are not deleted:** Planning is unimplemented and no cross-service cascade is claimed.

`boundaryAreaM2` and `boundaryPerimeterM` are calculated when a boundary exists, otherwise null. `summary.fieldCount` and `fieldAreaM2` count/sum **only independent Fields**, using gross `areaM2` (holes removed, before exclusions). Empty independent state yields zero. Embedded legacy fields contribute neither count nor area, even when they contain `areaM2`; this avoids double counting and does not imply migrated data. `activePlanCount` remains null, not a fabricated zero. Legacy JSONB and templates remain intact internally and are omitted from the public Farm resource.

## Field HTTP contract

- `GET /farms/{farmId}/fields?page=1&pageSize=20`: `{items,total,page,pageSize}`, oldest first with UUID tie-breaking, page size 1–100.
- `POST /farms/{farmId}/fields`: 201 Field.
- `GET /fields/{id}`, `PATCH /fields/{id}`: direct Field. PATCH is partial and validates the complete merged candidate before changing state or timestamps.
- `DELETE /fields/{id}`: empty 204; subsequent access returns 404.
- `POST /farms/{farmId}/fields:bulk`: 201 `{items}`. Entire batch validates before mutation; SQL inserts share one transaction. No partial imports.

Writable Field properties: required `name` (nonblank, up to 120 characters), `geometry` (Polygon); optional `excludedZones` (MultiPolygon|null), `soilType`/`cropType` (nonblank text up to 120 characters or null), `soilPh` (finite non-boolean number 0–14 or null), `irrigation` (`none|drip|sprinkler|flood|other`, default `none`), and `autoSpacing` (strict boolean, default false). Nullable properties default to null. Read-only properties: `id`, `farmId`, `createdAt`, `updatedAt`, `areaM2`, `netAreaM2`, `perimeterM`. Unknown/read-only input and empty PATCH receive 422.

### Explicit bulk import formats

Exactly one of these documents is accepted, with 1–100 entries and a maximum serialized RPC document length of 2,000,000 characters (2 MB for ASCII JSON):

```json
{"items":[{"name":"Example","geometry":{"type":"Polygon","coordinates":[[[10,50],[10.001,50],[10.001,50.001],[10,50.001],[10,50]]]}}]}
```

```json
{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"name":"Example","irrigation":"drip"},"geometry":{"type":"Polygon","coordinates":[[[10,50],[10.001,50],[10.001,50.001],[10,50.001],[10,50]]]}}]}
```

Feature properties accept the writable Field properties except geometry, which belongs only in Feature.geometry. Feature IDs, bbox, CRS declarations, other metadata, and arbitrary document wrappers are rejected, not silently discarded. Geometry is not guessed from legacy latitude/longitude lists. HTTP/OpenAPI schemas describe both formats.

## Geometry policy

Farm owns topology and containment validation, independently of gateway schema validation. Shapely/GEOS validates planar RFC 7946 topology in WGS84 longitude/latitude coordinates; pyproj/PROJ computes ellipsoidal WGS84 measurements in square metres/metres. No projected CRS, implicit axis conversion, raster resolution, or altitude is involved.

- Positions are exactly `[longitude,latitude]`, finite numeric values, never booleans. Longitude is −180 to 180; latitude is strictly between the poles. Antimeridian-spanning edges and overall longitude spans of 180 degrees or more are rejected rather than ambiguously unwrapped. This is a bounded agricultural polygon API, not global/polar geometry support.
- Rings must be explicitly closed with 4–5000 positions. A geometry allows at most 100 polygons, 100 rings per polygon, and 10000 total positions. Empty, zero-area, invalid/overlapping rings, holes outside their shell, and self-intersections are rejected. No silent repair, snapping, reorientation of stored coordinates, or simplification occurs.
- A Field, including its boundary, must be covered by the Farm boundary when present. A Field cannot occupy a Farm boundary hole. Null Farm boundary means no farm-containment constraint.
- Exclusions must form a valid MultiPolygon strictly inside the Field, without touching its exterior or holes. Polygon overlaps are rejected by GEOS topology validation. Point-touching exclusion components follow valid MultiPolygon semantics. Exclusion polygon holes are retained.
- `areaM2` is the Field polygon's ellipsoidal area with intrinsic holes removed. `netAreaM2` subtracts exclusion polygon areas, accounting for their holes; it must remain positive. `perimeterM` sums geodesic lengths of exterior and intrinsic-hole boundaries, not exclusion boundaries. Ring winding does not affect metrics. Boundary metrics use the same policy.

422 errors include `details[].path`, stable codes `self_intersecting`, `outside_farm_boundary`, `invalid_topology`, `outside_field`, or `invalid_value`. Bulk errors identify `items.<index>.<property>` even for FeatureCollection input. Gateway forwards only the constrained validation detail shape, not raw upstream messages or payloads.

## Persistence and security boundaries

Apply `migrations/002_create_fields.sql` after 001 before starting the updated PostgreSQL service; Compose's Farm migration task applies both. The additive `fields` table has an indexed `farm_id` FK with `ON DELETE CASCADE`; service-owned JSONB contains the Field projection. Existing farms.data fields/templates are not transformed. Field writes and boundary updates acquire the parent Farm row lock inside a transaction to serialize containment changes; JSON batches use the adapter lock and validate before mutation. SQL writes roll back on errors. No domain events/outbox delivery guarantee is claimed.

Ownership is checked by Farm for all Field operations, including imports and ID-only access; foreign/missing resources return 404. The internal RPC trusts the gateway's Identity-verified `owner_id`, not HTTP input. Internal authenticated transport and membership beyond sole ownership remain production-hardening gaps; never expose internal gRPC publicly. No tokens, personal fixtures, or real farm exports are needed for these tests.

## Validation and remaining gaps

Gateway tests cover schemas, CRUD, permissions/guests, containment, exclusions/holes, rollback, pagination, summaries, and cascades against JSON state. Service tests use generated contracts over real loopback gRPC, including malformed geometry and whole-batch/PATCH rollback. Tests generate Python contracts using `grpc_tools.protoc`; generated files remain ignored.

Run from repository root:

```sh
.venv/bin/python -m pytest -q services/farm-service/tests services/api-gateway/tests/test_farms.py services/api-gateway/tests/test_fields.py
.venv/bin/python -m pytest -q
```

Live PostgreSQL migration/transaction/concurrency acceptance, deployed-stack acceptance, Bruno execution, workers/outboxes, Planning cleanup, and full legacy/consumer parity are not established by JSON tests. No automatic legacy migration or migration-completion claim is made. Shared architecture/roadmap/development/provenance updates are coordinated separately by the parent task. AI-assisted implementation: OpenAI GPT-6.1-Sol.
