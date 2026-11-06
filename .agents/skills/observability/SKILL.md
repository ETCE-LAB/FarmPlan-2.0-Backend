---
name: observability
description: Add FarmPlan shared telemetry hooks and infrastructure configuration with safe low-cardinality metrics and HTTP-to-gRPC-to-job trace correlation.
---

# Observability

## Scope and preparation

Use for logging, metrics, tracing, operational signals, and troubleshooting, not domain logic or job delivery design. Read `docs/architecture.md`, `docs/roadmap.md`, `docs/development.md`, and `CONTRIBUTING.md`. Paths here are repository-root-relative. Inspect `packages/observability`, affected `services/`, and `infra/observability` before editing. The documented shared package is prepared but not instrumented; the observability stack is undecided. Do not claim collectors, dashboards, exporters, or enforcement exist without code/configuration evidence. Do not add a new dependency or infrastructure product without a concrete need.

## Workflow

1. Define a bounded operational question and acceptance signal, such as request errors, gRPC latency, job completion, retry exhaustion, or outbox backlog/oldest age. Distinguish process liveness from dependency readiness and successful domain work.
2. Put reusable instrumentation hooks in `packages/observability`; keep exporter, collector, sampling, retention, and deployment configuration in `infra/observability`. Keep domain-specific calls in their owning service, not domain persistence inside shared hooks. Inspect existing conventions before choosing APIs.
3. Correlate gateway HTTP, internal gRPC, outbox publication, job attempts, and result persistence. Define validated, size-bounded propagation of trace context across `services/api-gateway`, domain services, and `services/background-worker`. Treat incoming context as untrusted; never use it for authorization. Use span links or explicit parentage for delayed/duplicate work; distinguish logical jobs from individual attempts and close spans on failure/cancellation.
4. Use structured, redacted events with bounded operation names and outcomes. Exclude tokens, passwords, cookies, authorization headers, connection strings, personal/farm payloads, coordinates, signed URLs, and complete provider bodies from logs, span attributes, events, and metric labels. Sanitize exception messages and URL queries; use synthetic examples only.
5. Keep metric labels low-cardinality: service, route template, bounded operation, result category, or controlled error code. Never label by user/farm/job/event/trace IDs, raw paths, arbitrary URLs, exception text, or other unbounded values. Correlation identifiers belong only in appropriately controlled logs/traces, not metrics.
6. Bound telemetry queues, attribute sizes, export timeouts, and retries. Define sampling and retention deliberately. Exporter outages must not block business requests, change domain outcomes, or trigger recursive logging. Configure secrets through the environment, not committed configuration.
7. Specify actionable failure/backlog alerts and a troubleshooting path from request to job result. Report aggregate retries and terminal failures without claiming exactly-once delivery. Use `../database-outbox/SKILL.md` for delivery semantics rather than redesigning them through instrumentation.

## Acceptance checklist

- [ ] Tests demonstrate HTTP/gRPC/job correlation, duplicate-attempt handling, invalid/missing context, and success/error/cancellation paths.
- [ ] Captured logs, spans, and metrics exclude representative secrets and personal data; dynamic identifiers do not become metric labels.
- [ ] Exporter outage, queue saturation, and sampling behavior preserve domain outcomes and bounded resource use.
- [ ] Configuration and any alert examples use only approved, actually supported components; missing real collector integration is reported.
- [ ] Follow `../backend-validation/SKILL.md`; record exact checks, distinguish mocked hooks from end-to-end export, and document current versus target behavior accurately.
