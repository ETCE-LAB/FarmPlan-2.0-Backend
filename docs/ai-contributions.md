# AI contribution provenance

This record complements, and does not replace, the mandatory commit trailers and pull-request disclosures in [CONTRIBUTING.md](../CONTRIBUTING.md). Record exact provider/model identifiers, affected files or sections, assistance type, and validation. Never guess missing historical model identities. Do not store private prompts, credentials, or personal data.

## 2026-11-05 — Agent documentation and contribution policy

- **AI-assisted:** yes.
- **Provider/model:** OpenAI GPT-6.1-Sol, as reported by the current coding-agent environment.
- **Contribution policy scope:** `CONTRIBUTING.md`, the contribution/release/test rules in `AGENTS.md` and `CLAUDE.md`, `docs/README.md`, `docs/development.md`, `docs/roadmap.md`, `.agents/skills/backend-validation/SKILL.md`, and this record.
- **Assistance:** drafted the English contribution policy and aligned agent guidance with mandatory AI/model attribution, feature-branch-only changes, full-test gates, small commits, Conventional Commits, and the semantic-release target workflow.
- **Earlier work in this conversation:** the agent-documentation scaffolding and its English translation, the four `.agents/skills/*/SKILL.md` files, and `docs/legacy-feature-parity.md` were also AI-assisted. This record marks that documentation scope; it does not assert provenance for pre-existing application code or unrelated user changes.
- **Human review:** pending contributor review. AI-assisted material must be reviewed before merge.
- **Validation:** `python3 -m pytest` exited 2 during collection: Gateway and Identity could not import `grpc_tools`; no tests ran, so the full-test gate remains blocked. `git --no-pager diff --check` passed; a Python structure check validated local Markdown links and four skill frontmatters across 15 files. No commit, push, branch creation, release configuration, or release execution was performed. Documentation checks do not establish legacy parity or enforcement of hosting policies.

## 2026-11-05 — Missing skills, ADRs, and develop promotion policy

- **AI-assisted:** yes.
- **Provider/model:** OpenAI GPT-6.1-Sol.
- **Scope:** four added skills (`legacy-migration`, `media-pipeline`, `observability`, `contribution-release`), ADRs 0002–0006 and their index, updates to the existing skills and agent entry points, `CONTRIBUTING.md`, and documentation index/development/roadmap/provenance alignment.
- **Assistance:** analyzed documented gaps, drafted focused skill procedures and ADRs, removed stale inventory-pending instructions, and aligned feature → develop → main promotion and trusted main-only release rules. Existing ADR 0001 and application behavior are unchanged.
- **Validation:** installed existing declared dev dependencies into an ignored isolated Python 3.11 environment; `.venv/bin/python -m pytest` passed all 27 discovered tests, resolving the earlier system-environment collection blocker. No tests were excluded or skipped. Dependency deprecation warnings and missing domain/end-to-end/parity coverage remain explicit. No release automation, branch protection, or parity implementation was added.
- **Publishing state at preparation:** created `docs/agent-skills-decisions-workflow` at the user's request. The read-only remote query returned `main` but no `develop`; GitHub CLI authentication reported an invalid token. Publishing and PR creation require working authentication and an established target integration branch. The pre-existing user deletion of `.agents/.skills/TESTS.md` remains outside this contribution's staged scope.
- **Human review:** pending PR review. This record does not claim reviewed acceptance or configured enforcement.

## 2026-11-08 — Identity and gateway wishlist increment

- **AI-assisted:** yes.
- **Provider/model:** OpenAI GPT-6.1-Sol (coordinator and both implementation subagents).
- **Scope:** Identity protobuf additions, Identity implementation/migration/tests and lifecycle README; Gateway auth/user/module contracts, global errors, cookie transport, tests and README; affected Bruno requests; architecture, roadmap, development notes and this record. The pre-existing wishlist and deleted historical skill are user work, not attributed here.
- **Assistance:** implemented account lifecycle and typed camelCase HTTP contracts; documented deliberate response/error compatibility changes, session policy, and outstanding integration/cleanup work.
- **Validation:** `.venv/bin/python -m pytest -q` passed all 82 discovered tests with no skips. `git --no-pager diff --check` passed. Tests use mocked gRPC and an Identity SQL test double; real PostgreSQL migration/rollback/concurrency, live gRPC, browser/proxy, Bruno execution, and legacy parity checks were not run. Dependency/schema warnings remain visible. No branches, commits, pushes, deployments, or paid calls were performed.
- **Human review:** pending; missing integration validation prevents claiming production or merge readiness.

## 2026-11-08 — Farm wishlist and development JSON seed

- **AI-assisted:** yes.
- **Provider/model:** OpenAI GPT-6.1-Sol (coordinator and implementation subagent).
- **Scope:** Farm service implementation, synthetic seed, tests and README; Farm protobuf; Gateway Farm routes/tests; Farm Bruno requests; Compose adapter selection; architecture, roadmap, development and this record.
- **Assistance:** added typed Farm HTTP resources and ephemeral development mock storage without moving persistence into the gateway. Preserved legacy embedded data and documented unsupported geometry, Planning, and deletion cascades explicitly.
- **Validation:** `.venv/bin/python -m pytest -q` passed 88 tests without skips, including loopback gRPC using JSON state. Compose configuration and diff whitespace checks passed. PostgreSQL, deployed-stack, Bruno, and full legacy-parity acceptance remain unverified. Existing warnings remain. Branch `feat/farm-wishlist-mock` was created with user permission; no commit or push was made for this increment.
- **Human review:** pending. The pre-existing wishlist and historical skill deletion remain unrelated user work.

## 2026-11-08 — Independent Fields and geometry validation

- **AI-assisted:** yes.
- **Provider/model:** OpenAI GPT-6.1-Sol (coordinator and implementation subagent).
- **Scope:** Farm/Field protobuf, service geometry and resource modules, additive Field migration, JSON seed, requirements, tests and README; Gateway Field routes/models, Farm boundary schemas, tests and README; Compose dependency installation; Field Bruno requests; architecture, roadmap, development and this record.
- **Assistance:** implemented independent Field CRUD, atomic bulk import, owner isolation, bounded WGS84 topology and geodesic measurements, Farm-boundary validation and Field deletion cascades. Explicitly retained embedded legacy data without guessing migration or units; summaries now count only independent Fields. Planning/outbox behavior remains unimplemented.
- **Validation:** `.venv/bin/python -m pytest -q` passed all 128 tests without skips. Compose configuration and diff whitespace checks passed. Coverage includes loopback gRPC and transaction doubles; live PostgreSQL migration/concurrency/FK behavior, deployed-stack, Bruno and full parity acceptance remain unverified. Docker daemon access was denied. Existing dependency/schema warnings remain.
- **Git operations:** with user permission, committed the preceding Farm increment as `8c18d58` using author and committer date `2026-11-08T13:30:00+01:00`, then created `feat/field-wishlist`. The user subsequently requested a Field commit using the actual current time and publication of new local feature branches. The full 128-test suite, Compose validation, and whitespace checks passed again before preparation; publication does not establish integration or merge readiness. The wishlist and pre-existing historical skill deletion remain outside the commit.
- **Human review:** pending; incomplete integration checks block claiming production/merge readiness.

## 2026-11-14 — Authenticated overview and Docker migrations

- **AI-assisted:** yes.
- **Provider/model:** OpenAI GPT-6.1-Sol (coordinator and both implementation subagents).
- **Scope:** Farm protobuf and aggregate implementation; Gateway overview route/registration; overview service and gateway tests; Bruno overview request; Compose migration tasks; `scripts/run_sql_migrations.sh` and `scripts/test_sql_migrations.py`; architecture, development, roadmap, and this record.
- **Assistance:** implemented JWT-authenticated, owner-scoped Farm/independent Field counts and ordered discovery of all current repeatable service SQL migrations, including Identity sessions. Existing local environment changes, wishlist, and historical skill deletion are excluded from this attribution.
- **Validation:** `.venv/bin/python -m pytest -q` passed 151 tests without skips in the implementation run; targeted overview tests passed 17 and migration tests passed 6. Compose configuration, shell syntax, and diff whitespace checks passed. SQL tests use doubles; live PostgreSQL upgrades, rollback, deployed-stack acceptance, and Bruno execution remain unverified. Docker daemon access was denied. Existing dependency warnings remain.
- **Follow-up validation:** `.venv/bin/python -m pytest -q` passed all 153 tests without skips; Compose configuration and diff whitespace checks passed. Live stack validation remains unverified.
- **Follow-up scope:** renamed gateway liveness to `/health` in the route, Compose probe, Bruno request, tests, and documentation; made overview a global OpenAPI group independent of module flags, moved its Bruno request to `bruno/gateway/overview.bru`, and added regression coverage. Domain counting remains owned by Farm; no additional statistics are claimed implemented.
- **Git operations:** created `feat/authenticated-overview` at the user's request; no commit or push.
- **Human review:** pending; missing integration validation blocks claiming merge or production readiness.

## 2026-11-14 — Aggregated microservice health

- **AI-assisted:** yes.
- **Provider/model:** OpenAI GPT-6.1-Sol (coordinator and implementation subagent).
- **Scope:** Gateway health implementation/tests, Identity and Farm health registration, pinned health-protocol dependencies in their three requirements files, Compose health configuration, Bruno health request, architecture/development/roadmap, and this record.
- **Assistance:** added concurrent bounded standard gRPC health checks for all six existing microservices, sanitized per-service statuses, and aggregate HTTP `200`/`503` behavior. This does not claim database readiness or implemented domain behavior in placeholders.
- **Validation:** installed the declared `grpcio-health-checking==1.71.0` dependency into the ignored local environment. `.venv/bin/python -m pytest -q` passed 175 tests without skips, including real loopback health-protocol checks; existing dependency warnings remain. Compose and whitespace checks passed during implementation. Live Docker deployment, database readiness, and Bruno execution remain unverified.
- **Human review:** pending; no commit, push, or deployment was performed.

For commits containing this model's assistance, use `AI-Assisted: yes`, `AI-Model: OpenAI GPT-6.1-Sol`, and `Co-authored-by: OpenAI GPT-6.1-Sol <openai-gpt-6.1-sol@contributors.invalid>`. The non-deliverable address identifies the model for provenance; it is not a verified provider account.
