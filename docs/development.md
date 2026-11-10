# Development

[Index](README.md) · [Architecture](architecture.md)

All commands refer to the project root `FarmPlan-2.0-Backend`, not `backend-next/` as named in the existing root README. No installation was performed for this documentation.

## Previously executed read-only checks

```sh
docker compose version
docker compose -f infra/compose.yaml config --quiet
docker compose -f infra/compose.yaml config --services
python3 --version
python3 -m pytest --version
git --no-optional-locks status --short
```

Recorded results on November 5, 2026: Docker Compose `2.40.3+ds2-0ubuntu2`, valid Compose configuration, Python `3.14.8`, pytest `9.1.1`. The `python` command is unavailable in this environment; use `python3` here. An installed pytest version proves neither complete test dependencies nor a compatible service runtime. These are previously recorded checks, not a claim that this translation reran them.

Compose contains `postgres`, `redis`, `identity-migrations`, `identity-service`, `farm-migrations`, `farm-service`, `api-gateway`, `catalog-service`, `planning-service`, `analysis-service`, and `media-service`. It does not yet contain a `background-worker`.

## Working commands checked against configuration/code – not executed

The following commands have been checked against existing files but **have not been confirmed by runtime/integration testing**. They require Docker or an appropriately prepared Python environment. No dependencies were installed or containers started here.

```sh
docker compose -f infra/compose.yaml up --build -d
docker compose -f infra/compose.yaml ps
docker compose -f infra/compose.yaml logs api-gateway identity-service farm-service
curl --fail http://localhost:8000/healthz
docker compose -f infra/compose.yaml down
```

`up --build` may download images and packages and create containers/volumes. The two migration tasks run before their services and modify the local database. `down` stops the stack and preserves volumes. **`down -v` would delete PostgreSQL and Redis data** and is not a normal shutdown step.

Default endpoints from [Compose](../infra/compose.yaml): gateway `http://localhost:8000`, interactive API documentation `http://localhost:8000/docs` in development mode, PostgreSQL `127.0.0.1:5433`, and Redis `127.0.0.1:6380`. Internal gRPC addresses use Compose service names and port `50051`. `/healthz` confirms only the gateway response, not domain functionality across all modules. Interactive API documentation is disabled under `APP_ENV=production`.

A configuration template is available in [`.env.example`](../.env.example); the variables and defaults in Compose are authoritative. To explicitly load a previously prepared local `.env`:

```sh
docker compose --env-file .env -f infra/compose.yaml config --quiet
docker compose --env-file .env -f infra/compose.yaml up --build -d
```

This variant requires an existing `.env`. Do not commit secrets; Compose defaults are for local development only. Bind addresses, host ports, `APP_ENV`, `JWT_SECRET`, `ENABLED_MODULES`, and `GUEST_ENABLED_MODULES` are configurable. Enabled modules are not necessarily implemented modules.

### Identity wishlist migration and validation

Apply `services/identity-service/migrations/002_identity_sessions.sql` before starting the updated Identity service; use the existing migration task, which processes SQL files in filename order. It adds user credential versions/timestamps and hashed refresh sessions. No live migration was executed during this increment.

On November 8, 2026, `.venv/bin/python -m pytest -q` passed all 82 discovered tests without skips. Gateway tests mock gRPC and Identity tests use a SQL double, so live PostgreSQL migration/rollback/concurrency and gateway-to-service acceptance remain unverified. The run emitted pytest-asyncio, Starlette/AnyIO, and Pydantic alias-schema warnings; registration alias behavior is covered by tests. See the service READMEs for cookie/proxy policy and compatibility changes. Bruno requests were updated but not executed.

### Farm development mock mode

The [Farm service guide](../services/farm-service/README.md) documents `FARM_STORAGE_BACKEND=json` with `APP_ENV=development`. It loads synthetic seed data into memory, resets on restart, and does not bypass owner checks. Identity and existing Compose dependencies still require PostgreSQL. PostgreSQL remains the default Farm backend; no new central database service or background worker is introduced.

Farm increment validation: `.venv/bin/python -m pytest -q` passed 88 tests without skips. Tests include service-level loopback gRPC against JSON state; live PostgreSQL and full deployed-stack acceptance remain unverified. Existing dependency/schema warnings remain.

### Independent Fields

Apply `services/farm-service/migrations/002_create_fields.sql` before starting the PostgreSQL-backed service. It adds an indexed Field table with Farm FK deletion cascade and does not transform embedded legacy Fields. JSON development mode includes an independent synthetic Field. Farm summaries count only independent Fields, not retained embedded records.

Shapely and pyproj are declared service dependencies for topology validation and WGS84 geodesic measurements; the gateway development requirements include the Farm dependencies for in-process tests. Geometry uses GeoJSON longitude/latitude and metres/square metres, with bounded input and no silent repair. See the [service guide](../services/farm-service/README.md) for import formats and explicit global/polar limitations.

`.venv/bin/python -m pytest -q` passed all 128 tests without skips. Coverage includes Field ownership, geometry failures, bulk/PATCH rollback, loopback gRPC, and SQL transaction-double orchestration. Live PostgreSQL migration/FK/locking behavior, deployed-stack acceptance, and Bruno execution remain unverified; Docker daemon access was denied during the integration probe.

### Python tests

```sh
python3 -m pytest
```

Run this from the repository root to discover the full current Python suite, including Identity and Gateway tests. Test initialization may generate Protobuf code under `.generated/`. Development dependencies are described in [Identity requirements-dev](../services/identity-service/requirements-dev.txt) and [Gateway requirements-dev](../services/api-gateway/requirements-dev.txt). The initial `python3 -m pytest` attempt on November 5, 2026 exited 2 during collection because system Python lacked `grpc_tools`. The follow-up used an isolated Python 3.11 environment with the declared development dependencies: `.venv/bin/python -m pytest` passed all 27 discovered tests. This does not establish missing PostgreSQL/gRPC end-to-end or legacy parity coverage.

The environment used here lacks Python 3.11 `ensurepip`; creating `.venv` left an interpreter but could not bootstrap pip. The already available system pip populated that isolated environment with:

```sh
python3 -m pip --python .venv/bin/python install -r services/identity-service/requirements-dev.txt -r services/api-gateway/requirements-dev.txt
.venv/bin/python -m pytest
```

Dependency installation uses PyPI and may access the network. `.venv` and generated Protobuf files are ignored and must not be committed. On a normal environment with `venv` support, prefer creating a complete virtual environment and invoking its own pip. The test run reported deprecation warnings for the unset pytest-asyncio fixture-loop scope and a Starlette/AnyIO alias; these unrelated warnings were not suppressed or fixed.

Farm/Field now have dedicated tests under `services/farm-service/tests`, including loopback gRPC against JSON storage; these do not replace live PostgreSQL integration tests. This invocation cannot establish domain coverage for the health placeholders or the unimplemented worker.

## Workflows not yet available

There is currently no verified startup command for an outbox worker, no outbox migration, and no domain end-to-end invocation for Planning, Analysis, or Media. Add such commands only after implementation and verification; see the [roadmap](roadmap.md).

## Documentation and parity validation

Follow [CONTRIBUTING.md](../CONTRIBUTING.md): work on feature branches with PRs only to `develop`, never push directly to `develop` or `main`, promote only through a separately reviewed `develop` → `main` PR after the current `develop` revision and promotion checks pass the full suite and integration/acceptance validation, use Conventional Commits, and record exact-model AI attribution in commits, PRs, and [the provenance record](ai-contributions.md). Prefer small intermediate commits. The full repository test suite and all required checks must pass before every commit, push for review, and merge, including prose-only changes. Missing dependencies, unavailable integration infrastructure, failures, or unexecuted checks block readiness; no documentation-only exemption applies.

Maintain all documentation, agent instructions, and skills in clear English. Additionally check local links, skill frontmatter, technical identifiers/paths, current-versus-target distinctions, and `git --no-pager diff --check`. The Python command above covers current discovered tests, not absent domain/integration tests or future non-Python suites. Add their commands when implemented; do not mistake absent coverage for passing parity.

semantic-release, Conventional Commit/AI-trailer CI validation, and branch protection are required targets but are not configured yet. See the contribution guide for release policy and required hosting/CI controls.

Migration completion additionally requires the verified legacy inventory, explicit data/API compatibility decisions, and passing capability-level regression/acceptance tests described in the roadmap. Documentation checks alone do not establish functional parity.
