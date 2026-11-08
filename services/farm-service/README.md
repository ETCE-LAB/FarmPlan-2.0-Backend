# Farm service

Owner-scoped Farm CRUD is implemented over gRPC and exposed by the gateway under `/api/v1/farms`. PostgreSQL already exists and remains the default authoritative adapter; this increment does not replace it, change the schema, or implement workers/outboxes.

## Development JSON adapter

Set `FARM_STORAGE_BACKEND=json` and `APP_ENV=development` explicitly. With Compose:

```sh
APP_ENV=development FARM_STORAGE_BACKEND=json docker compose -f infra/compose.yaml up --build -d farm-service api-gateway
```

Compose still starts its existing PostgreSQL/migration dependencies (Identity also requires PostgreSQL). JSON mode does not use the Farm database. It loads `src/farmplan_farm/seed.json` into process-local mutable memory. Writes never modify the seed file. **This is not persistence:** restarting resets all changes; multiple replicas have independent state. No arbitrary seed paths or real user exports are loaded. Production and every non-development environment reject JSON mode; unknown adapters fail startup. Normal operation defaults to `FARM_STORAGE_BACKEND=postgres` and requires `DATABASE_URL`.

The synthetic fixture belongs exclusively to owner UUID `9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4`; farm UUID is `c56c779b-2ee1-4a15-af56-7a3c1c4fb3c8`. This is not a wildcard or an authentication bypass. An unrelated registered user sees an empty list and can create their own farms. The fixture does not create an Identity account or token. Tests supply the fixed identity through a test double, never a production impersonation endpoint.

## HTTP contract and compatibility

- `GET /api/v1/farms?page=1&pageSize=20`: `{items,total,page,pageSize}`; page starts at 1, page size is 1–100. Stable newest-first ordering, with UUID tie-breaking. Pages beyond the end are empty.
- `POST /api/v1/farms`: 201 direct Farm resource. Typed camelCase `name`, `location`, `climateZone`, `boundary`, `notes`, optional `contact: {ownerName,email}`. Legacy create payloads remain accepted as an adapter.
- `GET /api/v1/farms/{id}` and `PATCH /api/v1/farms/{id}`: direct Farm resource. PATCH is partial; empty updates, unknown/read-only fields, malformed UUIDs, null text, and invalid contact data are rejected. `contact:null` clears contact.
- Deprecated `PUT /api/v1/farms/{id}` accepts the existing partial legacy payload, including embedded `fields` and `template`; `createdAt` is ignored. New HTTP success responses intentionally replace the old status/farm wrappers. Consumers must migrate to direct resources and `items`.
- `DELETE /api/v1/farms/{id}`: empty 204. Deleting the Farm deletes its embedded JSON field/template data. No independent Fields or Plans exist here; cross-service Planning cascades are **not implemented**.

IDs are UUIDs. Timestamps are service-owned ISO 8601 UTC values from PostgreSQL columns or the development clock, not caller-supplied data. Existing JSONB is not rewritten/migrated by reads. PATCH uses a shallow top-level merge, preserving omitted fields, templates, and unknown legacy stored data internally. Legacy internals are intentionally not included in the public Farm projection. No data cutover or full legacy parity is claimed.

Contact is exposed only on owner-scoped resources. Foreign UUIDs return 404 for reads/mutations; lists contain only the verified owner. Guests are denied even if gateway module flags enable Farms. Internal gRPC continues to trust gateway-provided owner IDs, as before: do not expose it publicly; internal authenticated transport remains a production-hardening gap.

## Explicitly unavailable values

`boundary` accepts only null in this bounded increment; polygons receive 422 rather than accepting geometries without robust topology/geodesic validation. `boundaryAreaM2` and `boundaryPerimeterM` are null, never invented. Existing raw JSON geometry, if present, is retained internally, not converted or asserted valid. Polygon support requires a separately validated implementation using GeoJSON WGS84 `[longitude, latitude]`, square metres and metres.

`summary.fieldCount` counts existing embedded fields. `fieldAreaM2` sums only explicit finite nonnegative numeric `areaM2` values; missing/unknown units or invalid values yield null for the total. Empty fields yield 0. Legacy `area` or latitude/longitude polygons are not guessed to be square metres and are not converted. `activePlanCount` is null because there is no implemented Planning service; zero would incorrectly imply a verified count.

## Validation

Gateway Farm tests execute the real service application with JSON state and test transport validation, ownership, CRUD, legacy preservation, and configuration. Service tests exercise the generated contract over loopback gRPC with ephemeral storage. Neither proves live PostgreSQL migrations, transactional/concurrent behavior, worker/outbox delivery, Planning deletion, or full legacy migration parity. Generated Python contracts are created by `grpc_tools.protoc`, never edited manually.
