# Claude entry point for FarmPlan

Read and follow [AGENTS.md](AGENTS.md) first. It contains the shared architecture, security, and workflow rules, which are intentionally not duplicated here.

## Start of every task

1. Read [docs/README.md](docs/README.md) and the task-relevant documents.
2. Read [CONTRIBUTING.md](CONTRIBUTING.md). Run `git --no-optional-locks status --short` and `git --no-pager branch --show-current`; inspect affected code and preserve existing changes. Work on feature branches; PRs target `develop` only. Never push directly to `develop` or `main`. Promote to `main` only through a separate reviewed `develop` PR after the current integration revision and promotion checks fully pass. Obtain permission before creating branches or performing Git writes.
3. Load the appropriate project-local instructions by reading their `SKILL.md`:
   - [Backend feature](.agents/skills/backend-feature/SKILL.md)
   - [Database and outbox](.agents/skills/database-outbox/SKILL.md)
   - [Geospatial analysis and optimization](.agents/skills/geospatial-analysis/SKILL.md)
   - [Validation and review](.agents/skills/backend-validation/SKILL.md)
   - [Legacy migration](.agents/skills/legacy-migration/SKILL.md)
   - [Media pipeline](.agents/skills/media-pipeline/SKILL.md)
   - [Observability](.agents/skills/observability/SKILL.md)
   - [Contribution and release](.agents/skills/contribution-release/SKILL.md)
4. Define a bounded implementation increment with verifiable acceptance criteria. The roadmap is not a request for complete implementation.

## Orientation

- [Architecture: current state and target](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Development and checks](docs/development.md)
- [Architecture decisions](docs/decisions/README.md)
- [Legacy feature parity](docs/legacy-feature-parity.md) — source-inspected baseline; implementation and parity verification remain required.

The architecture diagram describes the target, not the full implementation state. A prepared directory, development stub, or successful health check does not establish a complete domain capability.

## Language and legacy parity

All maintained documentation, agent instructions, and skills, including new documentation, must be in clear English. Full functional parity with `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend` is mandatory: no legacy capability may be silently dropped. Map each capability to an owning service and regression/acceptance tests in the parity inventory. Do not blindly reproduce insecure behavior; document compatibility decisions and security corrections and test secure replacements. A verified inventory, explicit data/API compatibility decisions, and passing parity tests are required before migration completion; the linked inventory is not yet evidence of verification.

## Contribution gates

Follow the contribution rules in `AGENTS.md` and `CONTRIBUTING.md`: full tests/checks must pass before each small, coherent commit, push for review, and merge, including documentation-only work. Use Conventional Commits for semantic-release. Mark all AI-assisted work with the exact model, mandatory AI/model/co-author commit trailers, PR disclosure, and an updated [provenance record](docs/ai-contributions.md); preserve attribution in squash commits. Missing or failing checks block readiness. Release automation is a target, not yet implemented.

## Completion

Report concisely in English: changed files and behavior, checks actually executed and their results, and open points. Update affected documentation. No commits, branches, deployments, or paid calls without an explicit request.
