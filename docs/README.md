# FarmPlan Backend – Documentation

This documentation distinguishes the **current state**, verified against code and Compose, from the **target architecture**. An existing directory or enabled module does not prove that a domain capability is implemented.

## Getting started

- [Contribution rules: branches, test gates, AI attribution, and releases](../CONTRIBUTING.md)
- [AI contribution provenance](ai-contributions.md)

- [Architecture: current state, target design, and data flows](architecture.md)
- [Roadmap with priorities and acceptance criteria](roadmap.md)
- [Development and verified commands](development.md)
- [Legacy feature parity](legacy-feature-parity.md) — source-inspected baseline; implementation and verified parity remain outstanding.
- [Architecture decisions](decisions/README.md)
- [ADR 0001: service boundaries](decisions/0001-service-boundaries.md)

## Task-specific agent skills

Read [AGENTS.md](../AGENTS.md) first, then load only the instructions relevant to the task:

| Skill | Purpose |
| --- | --- |
| [Backend feature](../.agents/skills/backend-feature/SKILL.md) | Bounded FastAPI/gRPC domain increments |
| [Database and outbox](../.agents/skills/database-outbox/SKILL.md) | Service-owned persistence and reliable workers |
| [Geospatial analysis](../.agents/skills/geospatial-analysis/SKILL.md) | Raster, provider, and placement conventions |
| [Backend validation](../.agents/skills/backend-validation/SKILL.md) | Tests, security review, and honest validation reports |
| [Legacy migration](../.agents/skills/legacy-migration/SKILL.md) | Source audits, compatibility mappings, and parity fixtures |
| [Media pipeline](../.agents/skills/media-pipeline/SKILL.md) | Safe asynchronous image ingestion and attribution |
| [Observability](../.agents/skills/observability/SKILL.md) | Shared telemetry hooks and job correlation |
| [Contribution and release](../.agents/skills/contribution-release/SKILL.md) | Feature-to-develop PRs, promotion gates, AI attribution, and releases |

## Documentation language and migration requirements

All maintained documentation, agent instructions, and skills, including new documentation, must be written in clear English. Preserve technical identifiers and paths.

## Sources and scope

Primary sources include [Compose](../infra/compose.yaml), the [gateway code](../services/api-gateway/src/farmplan_gateway/main.py), [Identity](../services/identity-service/src/farmplan_identity/main.py), [Farm](../services/farm-service/src/farmplan_farm/main.py), and the [health placeholder](../scripts/dev_grpc_service.py). The [existing project overview](../README.md) partly describes goals; these are not assumed to be implemented here.

Review date: November 5, 2026. This documentation change contains no implementation and does not settle previously open technology, provider, or contract details.
