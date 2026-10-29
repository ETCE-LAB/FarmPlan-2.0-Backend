# FarmPlan Backend

From `backend-next/`:

```sh
docker compose -f infra/compose.yaml up --build
```

The public gateway listens on `http://localhost:8000`; interactive API docs are at `http://localhost:8000/docs`. PostgreSQL and Redis are available on host ports `5433` and `6380` (container ports `5432` and `6379`). Override `POSTGRES_PORT` or `REDIS_PORT` if those host ports are also occupied. Internal gRPC services are reachable by Compose service name on port `50051` and are not published to the host.

The Compose defaults are for local development only. If you already copied `.env.example` to `.env`, update `POSTGRES_PORT=5433` and `REDIS_PORT=6380` there because values in `.env` override Compose defaults. For a persistent local setup, copy `.env.example` to `.env` and replace the development secrets. The identity migration runs as a one-shot Compose task on startup and is safe to rerun; `down -v` removes all local PostgreSQL and Redis data.

```sh
python -m pip install -r services/identity-service/requirements-dev.txt -r services/api-gateway/requirements-dev.txt
python -m pytest services/identity-service/tests services/api-gateway/tests
```

```sh
bru run bruno/gateway --env local
```

## Service and worker layout

- `services/identity-service`: account and guest identity provider.
- `services/api-gateway`: public FastAPI routes and middleware.
- `services/farm-service`: farm, field, membership and farm-owned outbox.
- `services/catalog-service`: species/catalog domain and dataset jobs.
- `services/planning-service`: planning domain, placement optimizer, versioned rules and service-owned workers.
- `services/analysis-service`: soil, climate and geospatial analysis; external soil/weather/geocoding/GIS adapters and analysis workers.
- `services/media-service`: image metadata, object-storage adapters and media workers.
- `services/background-worker`: independently deployable job consumers/schedulers that call internal services over gRPC.

PostgreSQL tables and outbox data are owned by each service; `infra/postgres/` is for local database setup. Redis is a backing service. GeoTIFF/object storage and CDN configuration belongs under `infra/object-storage/` and the media/analysis adapters. Shared logging, metrics and tracing hooks live in `packages/observability/`; deployment-level configuration lives in `infra/observability/`.


## 12-Factor principles

1. One version-controlled codebase, deployed to multiple environments.
2. Explicit, reproducible dependencies per service.
3. Environment-based configuration; secrets are not committed.
4. Backing services are configured as attached resources.
5. Build, release and run are separate stages.
6. Services are stateless; persistent state belongs in backing services.
7. HTTP services bind to a port; internal services expose gRPC.
8. Scale using independent service processes.
9. Processes start quickly and shut down cleanly.
10. Keep development and production environments similar.
11. Write logs to stdout/stderr for the platform to collect.
12. Run migrations and admin tasks as explicit, versioned tasks.
