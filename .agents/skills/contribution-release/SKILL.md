---
name: contribution-release
description: Apply FarmPlan feature-to-develop PR and reviewed main promotion gates, exact-model AI attribution, Conventional Commits, and trusted main-only release policy.
---

# Contribution and release

## Scope and authority

Use when preparing contributions, reviewing attribution and promotion readiness, or planning release automation. Read `CONTRIBUTING.md`, `AGENTS.md`, `docs/development.md`, `docs/ai-contributions.md`, and the contribution gate in `docs/roadmap.md`. Paths here are repository-root-relative.

The workflow below follows `CONTRIBUTING.md`. Treat it as required policy, not evidence that `develop`, hosting protections, integration pipelines, or semantic-release are configured. Report discrepancies and do not install automation as part of an unrelated task.

## Permission and branch checklist

- [ ] Obtain explicit permission before any Git write, including branch creation, commits, pushes, merges, history rewrites, or tags, and before release/deployment actions. Policy is not authorization. If Git actions are prohibited, perform none, including read-only inspection, and report branch/tree state as unverified.
- [ ] When inspection is authorized, inspect the current branch and working tree without discarding user changes. If on `main` or `develop`, request permission to create/use a feature branch before committing; never reset work to switch branches.
- [ ] Target ordinary feature/fix/documentation PRs **only at `develop`**. Never open a feature branch PR directly to `main`.
- [ ] Promote **`develop` to `main` only through a reviewed promotion PR**, after the exact develop revision has fully passing repository and integration checks. Validate the promotion/merge revision with all required checks as well; rerun when either branch changes.
- [ ] Never directly push, force-push, or bypass protections on `develop` or `main`, including bots and administrators. Changes to either protected branch arrive through reviewed PRs with passing required checks. Do not force-push shared branches.

## Small verified contributions

1. Prefer small coherent commits with related tests and documentation. Use Conventional Commits for every commit and final PR/squash title: `<type>(<optional-scope>): <description>`. Preserve `!` and `BREAKING CHANGE:` migration details for incompatible changes; markers do not authorize breaking changes.
2. Use `../backend-validation/SKILL.md` for validation mechanics. Run targeted checks first, then the full repository suite and every required check before every commit, push for review, and merge, including documentation-only changes. `python3 -m pytest` is the documented current Python suite, not proof that every required integration/parity check exists.
3. Record exact commands, revision/scope, outcomes, and coverage gaps. Missing dependencies/infrastructure, absent required coverage, skipped checks, failures, or interrupted runs block readiness. Do not ignore/exclude tests or add skips to pass. Run the documented whitespace/diff check when Git inspection is allowed; otherwise report that check as not run.

## AI provenance checklist

- [ ] Disclose all materially incorporated AI assistance, including prose, tests, design, and review. Record scope and actual validation without private prompts or sensitive payloads.
- [ ] Each AI-assisted commit body identifies affected files/parts and validation and includes `AI-Assisted: yes`, an `AI-Model:` trailer with the exact provider and model/version for each contributing model, and a model-specific `Co-authored-by:` trailer for each model.
- [ ] Obtain actual model identifiers from the tool/session; never guess or substitute a product name for a model. Use the provider's documented attribution identity when available, otherwise a clearly non-personal, non-deliverable `.invalid` identity as permitted by `CONTRIBUTING.md`; do not impersonate an account.
- [ ] Include an AI assistance section in the PR with each model, scope, assistance type, and human review/validation. Maintain file-level provenance in `docs/ai-contributions.md` when file edits are authorized.
- [ ] Preserve every applicable model trailer/co-author and semantic/breaking-change marker through squash, rebase, cherry-pick, and promotion. Check the final merge message, not only intermediate commits.
- [ ] If scope forbids editing provenance or other required records, leave them untouched and report the unmet gate; do not claim contribution readiness.

## Release checklist

- [ ] Treat semantic-release as a target until implementation and enforcement are verified. No manual version bump, tag, publication, or improvised release workaround.
- [ ] Run semantic-release only in trusted CI on the successfully checked merged `main` revision after reviewed promotion. Never release from `develop`, feature branches, or untrusted PR code; no develop prereleases.
- [ ] Require fully passing develop and integration gates before promotion and passing required main checks before release. Validate version selection, breaking markers, credentials isolation, concurrency, and failure behavior when automation is explicitly in scope.
- [ ] Derive versions, release notes, and tags from Conventional Commits. Do not configure release-bot direct commits to either protected branch, including version/changelog commit plugins. Restrict release credentials to trusted release jobs; never expose them to fork PRs.
- [ ] Report verified enforcement separately from intended policy, and list any approval, attribution, validation, protection, or integration gap that blocks readiness. Do not perform Git writes or releases merely because this checklist is satisfied.
