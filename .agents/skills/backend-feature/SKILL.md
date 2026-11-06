---
name: backend-feature
description: Implement bounded FarmPlan domain capabilities through FastAPI and gRPC with correct service boundaries, permissions, and contract tests.
---

# Backend feature

## Preparation

Read `AGENTS.md`, `docs/architecture.md`, and the relevant section of `docs/roadmap.md`. Inspect affected gateway routes, service implementations, contracts under `packages/api-contracts`, and existing tests. Distinguish stubs from domain implementations.

Consult [the legacy feature parity inventory](../../../docs/legacy-feature-parity.md), a source-inspected baseline whose parity remains unverified. Full functional parity with `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend` is mandatory; no capability may be silently dropped. Map each affected capability to its owning service and regression/acceptance tests. Document data/API compatibility decisions and security corrections; test secure replacements instead of blindly copying insecure behavior. A verified inventory and passing parity tests are migration completion gates. Keep all maintained and new documentation, agent instructions, and skills in clear English.

## Workflow

1. Define the use case, owning domain, and acceptance criteria, including negative cases.
2. Keep HTTP transport and gRPC error mapping in `services/api-gateway`; implement domain rules in the responsible service.
3. Validate identity, guest permissions, and, where applicable, farm membership on the server. Do not treat client-supplied roles as authoritative.
4. Extend contracts compatibly. Identify the existing generator before changing generated code; do not edit generated files manually.
5. Persist only in service-owned tables. For migrations or asynchronous events, also load `../database-outbox/SKILL.md`.
6. Add targeted tests for success, invalid input, missing permissions, and relevant gRPC errors. Maintain affected Bruno requests without secrets.
7. Use `../backend-validation/SKILL.md` to finish, and update current-state documentation and the roadmap only to the extent supported by evidence.

## Done when

The vertical path is implemented, contracts and tests agree, no service boundary has been bypassed, and executed checks are documented. Explicitly identify incomplete work.
