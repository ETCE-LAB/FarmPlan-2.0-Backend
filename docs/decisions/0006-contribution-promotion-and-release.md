# ADR 0006: Reviewed promotion, exact AI attribution, and trusted releases

- Date: November 5, 2026
- Status: accepted policy; branch/CI/release enforcement outstanding
- References: [CONTRIBUTING](../../CONTRIBUTING.md), [Development](../development.md), [Roadmap](../roadmap.md)

## Context

The contribution guide already requires feature branches, full validation, Conventional Commits, exact-model AI attribution, reviewed merges, and semantic-release from trusted main CI. It states that release automation and CI enforcement are not configured. This ADR records the additional user requirement that integration must pass through `develop`. The contribution guide, agent instructions, skills, and roadmap express this same branch flow. The remote integration branch and hosting enforcement must be verified separately.

## Decision

### Branches and validation

- All changes, including fixes and documentation, start on feature branches. Feature pull requests target **only `develop`**, never `main`.
- No direct pushes to `develop` or `main`, including force pushes, administrative bypasses, and bot pushes. Both branches receive changes only through reviewed pull requests with passing required checks.
- `main` receives promotion pull requests **only from `develop`**. Promotion requires green checks on the current `develop` revision plus the full required checks and review for the promotion's final revision. Any subsequent change invalidates earlier evidence for that revision.
- Prefer small, coherent, working commits. Run the full repository test suite and all required checks before every commit, push for review, and merge, including documentation-only changes. Targeted checks help development but do not replace the full gate. Missing dependencies/infrastructure, unavailable checks, failures, or skips must be reported and block readiness; do not bypass them or manufacture a passing result.
- Check merged revisions as well. Release eligibility requires successful checks on the actual merged `main` revision, not merely its pre-merge PR.

### Attribution and commit semantics

- Use Conventional Commits and preserve semantic markers, including `!` and `BREAKING CHANGE:` migration details where required, in final squash messages.
- Every AI-assisted contribution requires `AI-Assisted: yes`, an `AI-Model:` entry with the exact provider/model/version for every contributing model, and model-specific `Co-authored-by:` trailers. Never guess an identity or substitute a generic tool name. Follow CONTRIBUTING's documented-provider identity or clearly non-personal `.invalid` fallback rules.
- Commit bodies describe assisted scope and actual validation. PRs disclose models and assistance, and the durable provenance record must be updated. Preserve all applicable attribution when squashing, rebasing, or cherry-picking; human reviewers remain responsible.

### Release authority

- semantic-release is the only release mechanism, running in trusted CI only after a reviewed merge to `main` and successful full checks on that merged revision. **No release runs on `develop`, feature branches, or pull requests.**
- Do not manually bump versions, tag, or publish to bypass automation. Until automation exists, do not improvise manual releases.
- Release credentials are confined to the trusted release job, never exposed to untrusted PR code. Serialize release jobs and derive versions/notes from Conventional Commits.
- Release automation must not push version/changelog commits directly to either protected branch. GitHub releases are the existing initial target; package/container publishing needs a separate explicit target and credentials decision.
- Policy is not authorization for an agent to create branches, commit, push, tag, release, or deploy. Each still requires an explicit user request.

## Alternatives considered

Feature-to-main PRs and direct pushes bypass the required integration/promotion sequence. Releasing from develop would publish an unpromoted integration revision. Manual releases or release-bot branch commits would bypass the release and review gates. Generic AI labels would lose model-level provenance. Documentation-only test exemptions would contradict the full validation policy. These alternatives are rejected.

## Consequences

Two reviewed integration stages add latency but separate integration from release eligibility. Branch protection, permitted PR sources/targets, required checks, review controls, attribution validation, and trusted release permissions need actual enforcement; policy prose alone is insufficient. CONTRIBUTING, roadmap, and workflow guidance must stay aligned with this decision. Missing validation blocks readiness even for these ADRs.

AI assistance for these decisions is recorded in [the provenance record](../ai-contributions.md); commit and PR attribution are required as well.

## Open questions

Required check identities, review counts, hosting protection configuration, merge strategy, promotion/squash handling that preserves semantic history and attribution, CI implementation, credential provisioning, and release concurrency controls remain unresolved. This ADR does not claim develop exists or protections/automation are installed.

## Verification and outstanding work

Verify hosting controls reject direct pushes and feature-to-main PRs, allow feature-to-develop PRs only after full checks/review, and allow develop-to-main promotion only with green develop and full promotion checks/review. Test stale checks, failures, unavailable checks, and attribution preservation. Verify Conventional Commit version selection, breaking changes, trusted merged-main checks, credential isolation, serialized releases, and absence of develop/PR releases or release-bot branch pushes. Record exact commands and evidence; no CI or hosting enforcement is implemented by this ADR.
