# Instructions for AI agents

## Getting started and sources

- Read `docs/README.md` first, then [CONTRIBUTING.md](CONTRIBUTING.md) and the documents relevant to the task.
- `docs/architecture.md` describes the current state and target architecture; `docs/roadmap.md` describes implementation steps; `docs/development.md` covers development and checks.
- Architecture decisions are under `docs/decisions/`. Distinguish existing decisions, proposals, and open questions.
- Code and configuration establish the current state. Document discrepancies instead of treating planned capabilities as implemented.
- This file is the shared source of rules. `CLAUDE.md` is the Claude entry point.
- All maintained documentation, agent instructions, and skills, including new documentation, must be written in clear English. Preserve technical identifiers, paths, skill names, and valid frontmatter.

## Mandatory legacy functional parity

- Full functional parity with the legacy backend at `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend` is mandatory. No legacy capability may be silently dropped.
- Consult [the legacy feature parity inventory](docs/legacy-feature-parity.md). It is a source-inspected baseline, not proof of implemented or tested parity; keep gaps and verification status explicit.
- Map every legacy capability to an owning service and regression/acceptance tests. Track missing implementations and coverage explicitly.
- Do not blindly copy insecure behavior. Document security corrections and data/API compatibility decisions, preserve the legitimate capability through a secure replacement, and test it.
- Do not declare migration complete before the feature inventory is verified, data/API compatibility decisions are explicit, and parity tests pass for every capability. Follow the gates in `docs/roadmap.md`.

## Architecture boundaries

- Public HTTP goes through `services/api-gateway` (FastAPI); internal service communication follows the existing gRPC contracts under `packages/api-contracts`.
- Domains: Identity, Farm/Field, Catalog, Planning/Placement, Analysis, and Media. Use the existing directories under `services/`; do not introduce a new service split without a justified decision.
- Each service owns its tables and migrations. No direct access to other services' tables and no cross-service SQL joins.
- The gateway handles transport, authentication, and routing, not other services' domain persistence.
- Long-running analysis, import, image, and optimization work belongs in workers, not HTTP requests.
- Target: store the domain change and its outbox entry in the same PostgreSQL transaction. Plan for at-least-once delivery, idempotent processing, and bounded retries; do not claim an exactly-once guarantee.
- Redis is a cache/temporary state, not the authoritative data source. Binary data and GeoTIFFs belong in object storage, metadata in the responsible service.
- External Soil/Weather/Geocoding/GIS providers are integrated through Analysis adapters; Placement belongs to Planning, images to Media.

## Change workflow

1. Inspect the working tree, affected code, contracts, tests, and documentation. Preserve existing user changes.
2. Select the appropriate skill from `.agents/skills/` and read its `SKILL.md`. Skills are work instructions, not executable implementations.
3. Implement a small vertical increment with clear acceptance criteria. Do not implement the entire roadmap without a request.
4. Update affected contracts, migrations, tests, and documentation together. Change generated files only through the designated generator.
5. Start with targeted checks, then run the full repository test suite and all required checks. All tests must pass before every commit, push for review, and merge, including documentation changes. Missing dependencies/infrastructure, skipped required checks, or failures block readiness; report exact commands, results, and gaps. Do not claim success without execution.
6. Keep the current-state documentation and completed roadmap items up to date. Record significant boundary changes as an ADR.

## Contribution, attribution, and release rules

- Follow [CONTRIBUTING.md](CONTRIBUTING.md): feature branches may merge only through reviewed PRs into `develop`. Never push directly to `develop` or `main`, including bot or force pushes. Promote only through a separate reviewed `develop` → `main` PR after the current `develop` revision passes the full suite, required checks, and integration/acceptance validation; promotion checks must pass too. No direct feature-to-main PRs and no releases from `develop`.
- Prefer small, coherent intermediate commits that pass all tests. Use Conventional Commits and preserve semantic-release markers, including breaking-change details.
- Mark every AI-assisted contribution in commit bodies, PR disclosures, and [the provenance record](docs/ai-contributions.md). Require `AI-Assisted: yes`, exact provider/model in `AI-Model:`, and a model-specific `Co-authored-by:` trailer for every contributing model. Never guess the model identity; preserve trailers when squashing.
- semantic-release is the target release mechanism, not currently installed automation. Do not manually bump versions, tag, publish, or add a release bot that directly pushes commits to `main`.
- These policies do not authorize Git operations. Obtain an explicit request before creating branches, committing, pushing, tagging, releasing, or deploying. If on `main`, report it and obtain permission to create a feature branch before committing.

## Security and quality

- Trust neither request data nor client-supplied roles, user IDs, or farm IDs. Check permissions in the responsible service, including guest access and farm membership.
- No secrets, tokens, passwords, personal data, or complete external payloads in logs or examples. Configure through the environment; do not commit `.env`.
- External calls require timeouts, bounded retries, and understandable errors. Respect quotas, costs, and privacy.
- For geospatial data, handle CRS, units, coordinate order, and raster resolution explicitly. No implicit conversions.
- Use `packages/observability` for shared hooks; log/metric/trace configuration belongs under `infra/observability`. No high-cardinality metric labels.
- No new dependencies, infrastructure products, or incompatible contracts without a concrete need. Destructive migrations and deletions require explicit approval.
- No commits, branches, deployments, or paid API calls without a request.

## Skill directory

| Skill | Purpose |
| --- | --- |
| `.agents/skills/backend-feature/SKILL.md` | Domain capabilities, FastAPI/gRPC, service boundaries |
| `.agents/skills/database-outbox/SKILL.md` | PostgreSQL, migrations, outbox, workers |
| `.agents/skills/geospatial-analysis/SKILL.md` | Analysis, GeoTIFF, external GIS data, optimization |
| `.agents/skills/backend-validation/SKILL.md` | Tests, regressions, review, and validation |
| `.agents/skills/legacy-migration/SKILL.md` | Legacy source/consumer audits, data/API compatibility, parity fixtures |
| `.agents/skills/media-pipeline/SKILL.md` | Asynchronous images, attribution, safe fetching, storage consistency |
| `.agents/skills/observability/SKILL.md` | Shared telemetry hooks, infrastructure configuration, job correlation |
| `.agents/skills/contribution-release/SKILL.md` | AI attribution, feature-to-develop PRs, main promotion, semantic-release |

The historical path `.agents/.skills/TESTS.md` was removed; do not restore it. Create new skills only under `.agents/skills/<name>/SKILL.md`.
