---
name: backend-validation
description: Validate FarmPlan changes through targeted tests, contract and security review, and an honest report of executed and missing checks.
---

# Validation and review

Read `AGENTS.md`, `CONTRIBUTING.md`, and `docs/development.md`. Inspect the working tree and diff without reverting other people's changes. All maintained and new documentation, agent instructions, and skills must be in clear English.

## Validation plan

1. Map every behavior change to an acceptance criterion and a test.
2. Determine test commands and dependencies from the repository. Start with affected tests, then run the full repository suite and all required checks before every commit, push for review, and merge. This includes documentation-only changes. Missing dependencies/infrastructure, required checks not run, or failing tests block readiness. Do not install new dependencies merely to bypass an error.
3. For HTTP/gRPC, check validation, unauthenticated requests, guest access, other farms' IDs, error mapping, and contract compatibility.
4. For persistence, check service ownership, migrations, transaction rollback, and outbox atomicity. For workers, check duplicates, retries, and crashes. Mocks do not prove real database properties.
5. Check configuration and logs for secrets and personal data. Check external adapters for timeouts and bounded retries.
6. Check documentation links, skill frontmatter, current/target distinctions, and the updated roadmap. A health check is not a domain test.
7. Check [the legacy feature parity inventory](../../../docs/legacy-feature-parity.md), a source-inspected baseline with unverified parity, against the legacy backend at `/home/fingadumbledore/Documents/allgemein/studium/wintersemester_26_27/projekt/FarmPlan/backend`. Full functional parity is mandatory: no capability may be silently dropped. Require an owning service and regression/acceptance tests for every capability, explicit data/API compatibility decisions, and documented security corrections with tested secure replacements rather than blindly copied insecure behavior. Missing inventory verification or missing/failing parity tests block migration completion; do not claim parity from health checks or mocks alone.
8. Run `git --no-pager diff --check` and appropriate documentation structure/link checks in addition to the full tests; there is no prose-only exemption from the test gate.
9. Verify feature-branch workflow, Conventional Commits, AI-assisted scope disclosure, exact-model `AI-Model:` and `Co-authored-by:` trailers, and the updated `docs/ai-contributions.md` record. Preserve semantic-release markers and all attribution in the final squash message. Feature PRs must target `develop` only; promote `develop` to `main` only through a separate reviewed PR after the current integration revision, full suite, acceptance checks, and promotion checks pass. Never push directly to `develop` or `main`; never perform Git writes without an explicit request.

## Final report

List changed files, verified requirements, exact executed commands, and results. Report missing tools, missing infrastructure, and integration tests not run. Do not claim a successful check without executing it. Fix self-introduced errors with focused changes; do not fix unrelated or other people's errors in passing.
