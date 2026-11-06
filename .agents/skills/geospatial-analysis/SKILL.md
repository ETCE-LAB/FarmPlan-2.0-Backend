---
name: geospatial-analysis
description: Work on FarmPlan geospatial analysis, GeoTIFFs, Soil/Weather/Geocoding/GIS adapters, or placement optimization with explicit geospatial conventions.
---

# Geospatial analysis and optimization

Read `AGENTS.md`, `docs/architecture.md`, and affected contracts. Inspect existing implementations and dependencies before choosing technologies or providers.

Consult [the legacy feature parity inventory](../../../docs/legacy-feature-parity.md), a source-inspected baseline whose parity remains unverified. Full functional parity with `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend` is mandatory; no legacy analysis, integration, or optimization capability may be silently dropped. Map each to an owning service and regression/acceptance tests, including numerical/geospatial behavior and compatibility decisions. Do not blindly reproduce insecure behavior; document corrections and test secure replacements. A verified inventory, explicit data/API compatibility decisions, and passing parity tests are required before migration completion. Maintain all documentation, agent instructions, and skills, including new documentation, in clear English.

## Ownership

- `services/analysis-service`: geospatial analysis and external Soil/Weather/Geocoding/GIS adapters.
- `services/planning-service`: placement, optimization rules, and planning results.
- `services/media-service`: images and image metadata.
- Long-running computations run in workers. Binary data resides in object storage; references and metadata belong to the responsible service.

## Workflow

1. Explicitly define CRS/EPSG, axis and coordinate order, units, spatial resolution, time reference, and NoData behavior. Convert only deliberately and traceably.
2. Validate geometries and input sizes; bound raster size, runtime, and memory usage. Handle empty coverage and incomplete data.
3. Encapsulate providers behind Analysis adapters with timeouts, bounded retries, quota handling, and understandable errors. Check licensing, costs, and privacy before real calls.
4. Version datasets and rules so results are traceable. For optimization, define objectives, hard/soft constraints, and a reproducible seed where applicable.
5. Provide traceable job status for asynchronous work instead of long-running HTTP processing. Use `../database-outbox/SKILL.md` for persistent job/outbox changes.
6. Test with small local synthetic fixtures: swapped axes, incorrect CRS, NoData, edge cases, and provider failures. No paid live calls as default tests.
7. Finish with `../backend-validation/SKILL.md` and document assumptions and limitations of results.
