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

For commits containing this model's assistance, use `AI-Assisted: yes`, `AI-Model: OpenAI GPT-6.1-Sol`, and `Co-authored-by: OpenAI GPT-6.1-Sol <openai-gpt-6.1-sol@contributors.invalid>`. The non-deliverable address identifies the model for provenance; it is not a verified provider account.
