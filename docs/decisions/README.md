# Architecture decisions

[Index](../README.md) · [Architecture](../architecture.md) · [Roadmap](../roadmap.md)

| ADR | Status | Subject |
| --- | --- | --- |
| [0001 – Service boundaries](0001-service-boundaries.md) | Existing service split documented; target rules recorded | Responsibilities, data ownership, and worker boundaries |
| [0002 – Persistence and reliable workers](0002-persistence-and-reliable-workers.md) | Accepted target policy; implementation outstanding | Service-owned PostgreSQL, atomic outboxes, at-least-once delivery, idempotency, and bounded retries |
| [0003 – Gateway, contracts, and security](0003-gateway-contracts-and-security.md) | Accepted target policy; partially implemented | Public FastAPI boundary, versioned gRPC, and service-enforced authorization |
| [0004 – Storage, cache, and adapters](0004-storage-cache-and-adapter-ownership.md) | Accepted target policy; implementation outstanding | Object storage for binaries, non-authoritative Redis, and domain adapter ownership |
| [0005 – Legacy parity and secure compatibility](0005-legacy-parity-and-secure-compatibility.md) | Accepted migration policy; parity unverified | Mandatory capability coverage, explicit compatibility, secure corrections, and completion gates |
| [0006 – Contribution, promotion, and release](0006-contribution-promotion-and-release.md) | Accepted policy; enforcement outstanding | Feature → develop → main, full test gates, exact AI attribution, and trusted main-only semantic-release |

ADRs distinguish verified current behavior, accepted policy, implementation outstanding, and unresolved technical details. Acceptance of a policy is not evidence of deployed enforcement or functional completion. Gateway, Identity, and Farm have domain runtime code; Catalog, Planning, Analysis, and Media remain health placeholders, and the worker is unimplemented according to the current architecture documentation.

ADRs 0002–0005 elaborate established target policies without replacing ADR 0001 or choosing a broker, physical database topology, storage/provider product, or other unresolved infrastructure. ADR 0006 adds the explicit user requirement that feature PRs target only `develop`, promotion PRs to `main` come only from green `develop` with full checks/review, neither branch accepts direct pushes, and develop never releases. The contribution guide, roadmap, agent instructions, and skills must remain aligned with this policy.

The [legacy inventory](../legacy-feature-parity.md) now exists as a source-inspected baseline, but its required capabilities remain parity-unverified. Older references calling the inventory pending do not establish either its absence or completed parity.

New ADRs should include context, status, decision, alternatives, consequences, open questions, and verification expectations. Continue the numbering; later changes should explicitly supersede decisions rather than silently rewrite their history. Maintain all ADRs in clear English.

AI assistance for these records is documented in [the provenance record](../ai-contributions.md). See [CONTRIBUTING.md](../../CONTRIBUTING.md) for commit and PR attribution rules.
