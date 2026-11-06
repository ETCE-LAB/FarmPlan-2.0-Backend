# Contributing to FarmPlan

These rules apply to every contribution, including code, tests, documentation, configuration, generated artifacts, and AI-assisted work. Read [AGENTS.md](AGENTS.md), the [documentation index](docs/README.md), and the [development guide](docs/development.md) before making changes. All maintained documentation, agent instructions, and skills must be in clear English.

## 1. Feature branches and pull requests

- **Never push directly to `develop` or `main`.** This includes force pushes, bot pushes, and administrative bypasses. Feature branches must open reviewed pull requests **only into `develop`**, not directly into `main`.
- Promote changes to `main` only through a separate reviewed **`develop` → `main` pull request**, after the exact current `develop` revision passes the full test suite, all required checks, and integration/acceptance validation. A feature PR's checks alone do not prove the merged integration branch is healthy. Require the promotion PR checks and review too; changes to `develop` invalidate stale promotion results.
- The flow is `feature branch → develop → main`. Do not merge or release as part of merely pushing a feature branch or opening its PR. `develop` is not a release branch.
- Work on a feature branch, including for fixes and documentation. Use descriptive names such as `feat/catalog-search`, `fix/hardiness-validation`, or `docs/contribution-rules`.
- Check the current branch and working tree before starting. If already on `main`, move the work to a feature branch before committing. Preserve existing changes; never reset or discard them to change branches.
- AI agents must still obtain explicit permission before creating branches, committing, pushing, tagging, deploying, or invoking paid services. A workflow policy is not permission to perform these actions.
- Do not force-push shared branches. Any history rewrite of a personal feature branch requires coordination and must preserve AI attribution.

## 2. Small, verified commits

Prefer small, coherent intermediate commits over one large final commit. Each commit should represent a reviewable change, include its related tests/documentation, and leave the branch in a working state. Do not create deliberately broken checkpoint commits just to show progress.

Before **every commit**, run the full repository test suite and all available required validation checks. Start with targeted tests while developing, but targeted tests alone are not the final gate. **All tests must pass** before committing, pushing for review, or merging. This also applies to documentation-only changes. Rerun after changes and against the final pull-request revision; do not treat an earlier passing run as proof for later edits.

- Include unit, integration, contract, acceptance, security, and parity tests that exist for the repository. Provision their required services and fixtures safely.
- No ignored failures, `--ignore` exclusions, disabled tests, or newly introduced skips just to make a contribution pass. Any existing skips or unavailable checks must be reported; they are not evidence of successful coverage.
- Missing dependencies, unavailable infrastructure, interrupted runs, or failing tests mean **the gate is not satisfied**. Report the blocker; do not claim readiness or bypass it. Documentation checks alone do not replace this gate.
- Run `git --no-pager diff --check` and inspect the diff for secrets, unintended changes, and generated artifacts.
- Record exact commands, outcomes, and any missing coverage in the pull request. See [development and checks](docs/development.md) for commands and current gaps.

## 3. Mandatory AI disclosure and co-authorship

**Everything created or materially changed with AI assistance must be marked as AI-assisted and co-authored with the exact model used.** This includes code, documentation, tests, configuration, generated content, and substantive AI review/design incorporated into the contribution. Human authors remain responsible for accuracy, security, licensing, and validation.

### Commit requirements

Every commit containing AI-assisted work must include:

1. An `AI-Assisted: yes` trailer.
2. An `AI-Model:` trailer naming the exact provider and model/version reported by the tool. If several models contributed, list each separately. Never guess a model identity; obtain the actual identifier before committing.
3. A standard `Co-authored-by:` trailer for each contributing model, with the model/version in the name. Use the provider's documented attribution identity when available. Otherwise use a clearly non-personal, non-deliverable `.invalid` identity as in the example; do not impersonate a person or invent a verified provider account.
4. A body describing which files or parts were AI-assisted and how they were verified.

Example (use this model only when it was actually used):

```text
docs(contributing): define contribution and AI attribution rules

AI-assisted scope: CONTRIBUTING.md and related agent workflow guidance.
Validation: describe the actual commands and results here.

AI-Assisted: yes
AI-Model: OpenAI GPT-6.1-Sol
Co-authored-by: OpenAI GPT-6.1-Sol <openai-gpt-6.1-sol@contributors.invalid>
```

Do not replace these trailers with a vague reference to "AI", "Copilot", or "Claude" without the actual model. Do not claim tests passed unless they ran successfully. A `Co-authored-by` trailer records provenance; it does not create a verified GitHub account identity.

### Pull requests and artifact marking

- Include an **AI assistance** section listing each model, affected files/parts, the type of assistance, and human review/validation performed. State `AI assistance: none` only when true.
- Track durable file-level provenance in [docs/ai-contributions.md](docs/ai-contributions.md). Update it for AI-assisted changes, including documentation. Describe scope precisely; do not label unrelated human work as AI-generated.
- Commit trailers, the PR disclosure, and the provenance record are mandatory together. Inline comments in every source file are not required and must not break generated files or data formats.
- Preserve attribution when rebasing, cherry-picking, or squashing. The final squash commit must retain all applicable model trailers and co-authors; reviewers must check this before merging.
- Never include private prompts, credentials, personal data, or sensitive model payloads in disclosure records.

## 4. Conventional Commits and semantic-release

Use **Conventional Commits** for every commit and the final pull-request/squash title:

```text
<type>(<optional-scope>): <short description>
```

Examples:

```text
feat(catalog): add paginated species search
fix(analysis): reject degenerate field polygons
docs(agents): clarify service ownership
test(media): cover duplicate image jobs
ci(release): configure semantic-release
```

Release policy follows semantic versioning through **semantic-release**:

| Change | Commit marker | Version effect |
| --- | --- | --- |
| Backward-compatible feature | `feat` | Minor |
| Backward-compatible bug fix | `fix` or `perf` | Patch |
| Breaking public API, contract, or behavior change | `!` and a `BREAKING CHANGE:` footer explaining migration | Major |
| Documentation, tests, refactoring without behavior change, build, CI, or maintenance | `docs`, `test`, `refactor`, `build`, `ci`, `chore`, `style` | No release by default |

Breaking changes still require an explicit compatibility/migration decision and approval; a marker does not grant permission. Include AI trailers as well when applicable. Do not manually bump versions, create release tags, or publish releases to bypass the automated workflow.

### Automation status and target

**semantic-release and CI enforcement are not configured in this repository yet.** This document establishes policy, not a claim that the platform enforces it. Until release automation exists, do not improvise a manual release; implementing and validating it is a separate task.

The intended setup must:

- Run all tests/checks on feature PRs targeting `develop`, on the merged `develop` revision, on `develop` → `main` promotion PRs, and on merged `main`. Promotion requires a fully green current `develop`, integration/acceptance validation, passing promotion checks, and review.
- Protect both `develop` and `main` against direct pushes, force pushes, deletions, and bypasses; apply equivalent restrictions to automation accounts. Enforce PR base/source restrictions: feature PRs only to `develop`, and `main` promotion only from `develop`. Hosting settings must be configured separately.
- Validate Conventional Commits/final squash messages and required AI disclosures/trailers.
- Run semantic-release only from trusted CI after a successful merge to `main`, never on `develop`, feature branches, or untrusted pull-request code with release credentials.
- Derive the next version and release notes from Conventional Commits, create tags/releases, and serialize release jobs. Target GitHub releases initially; any package/container publication requires an explicit target and credentials decision.
- Avoid commits pushed by a release bot to `main`; do not use a version/changelog commit plugin that bypasses the pull-request policy. Version metadata and release notes must be produced without direct branch pushes.
- Keep credentials restricted to the release job and never expose them to fork pull requests.

## 5. Pull-request checklist

- [ ] Feature PR targets `develop`; no direct push to `develop` or `main`, and no feature PR targets `main`.
- [ ] For a promotion PR: source is `develop`, target is `main`, the exact current integration revision passes all tests/checks and acceptance validation, and promotion checks/review are complete.
- [ ] Small, coherent commits using Conventional Commits.
- [ ] Full test suite and all required checks passed for each commit and the final revision; exact commands/results recorded.
- [ ] No unavailable, skipped, or failing checks presented as successful validation.
- [ ] AI assistance declared, exact models identified, commit trailers present, provenance record updated.
- [ ] Final squash message preserves semantic markers, breaking-change details, and all AI co-authors.
- [ ] Service boundaries, permissions, contracts, migrations, and legacy parity reviewed as applicable.
- [ ] Documentation updated; no secrets, unrelated changes, or unsupported implementation claims.
