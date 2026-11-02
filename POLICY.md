# lina-system repository policy

This policy applies to every lina-system repository: lina, lina-app and lina-os. It sets the common rules for branches, pull requests, verification, review, merging, the changelog, versions and releases.

During the alpha the rules are kept small on purpose: required checks named by each repository, one automated review, merge commits, and a changelog line per pull request. Each repository adds what is specific to it, such as its build, test and QA commands, in its own docs. A repository's docs may add to this policy but not contradict it.

| Repository | What it is | CI |
| --- | --- | --- |
| [lina](https://github.com/lina-system/lina) | A full fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT, Nous Research). Upstream changes are taken selectively; see [docs/forking.md](https://github.com/lina-system/lina/blob/dev/docs/forking.md). | Required checks are listed in its [docs/delivery.md](https://github.com/lina-system/lina/blob/dev/docs/delivery.md) |
| [lina-app](https://github.com/lina-system/lina-app) | The desktop and mobile app. No code yet. | None until it has code |
| [lina-os](https://github.com/lina-system/lina-os) | An optional Linux distribution. No code yet. | None until it has code |

All three are public and licensed under the GNU Affero General Public License v3.0 (`AGPL-3.0-only`).

A worker is a coding tool or agent working on a repository.

## 1. Branches

- `dev` is the default and integration branch. Every pull request targets `dev`.
- `main` is the release branch. It moves forward from `dev` only when a release is made, and the release commit is tagged.
- lina also has `upstream`: Hermes `main` exactly as upstream has it. Nobody commits to it; it only fast-forwards to a newer upstream commit. Upstream commits reach `dev` only by a reviewed merge or cherry-pick, following [docs/forking.md](https://github.com/lina-system/lina/blob/dev/docs/forking.md).
- Pull requests into `main` are refused.
- Work on a short-lived branch from the latest `dev`, in its own worktree, with one coherent change. Never commit to `dev` or `main` directly.
- Keep other people's and other workers' branches and worktrees. Check the owner before deleting a branch.

## 2. Issues and pull requests

- Issues, pull requests, branch names, commit messages and reviews are in English, whatever language the work was requested in. Quoted source text, logs and code stay unchanged.
- Commit and pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), for example `fix(memory): keep forgotten items out of recall`.
- One pull request per issue. Link it with `Closes #<number>`. Change only what the issue asks; file anything else as a new issue.
- The pull request body says what changed and why, the observed behaviour, the QA evidence and the remaining risk. Claim only what the diff or a command you ran shows.
- A change that touches a trust boundary (credentials, configuration loading, tool permissions, install or update, network endpoints) says what it could weaken and how it was checked.
- Never put credentials, personal data or real conversations in an issue, commit, screenshot or fixture. Use synthetic data.

## 3. Verification

- "It typechecks" or "the tests are green" is not QA. Drive the real surface the change affects and record what you observed. Summarize the evidence in the pull request body; do not commit evidence files.
- Only public repositories use GitHub Actions. Private repositories (for example hermes-ops and its dashboard) run no GitHub CI; their tests are run locally and the result is written in the pull request body.
- Each repository lists its required checks in its own `docs/delivery.md`. A repository without code has no workflows and no required checks.
- Every required check is green on the current head before merge.
- A required check that is already red on `dev` is a defect of `dev` and still blocks the merge. Reproduce it, fix the cause in this pull request or a separate one, and rerun every required check.
- A red check blocks only the merge. It does not stop new work from starting.
- Never make a check pass by skipping tests, weakening assertions, adding retries, `continue-on-error`, excluding a platform or working around one environment. A smaller failure count is not a green result.
- Tests assert behaviour: state, IDs, structured fields, exit codes and events. They wait for an observed event, never a fixed sleep. Do not pin prose with a test.
- A fix for a race or concurrency bug closes its issue only after the original reproducer passes on the fix commit, recorded in the issue as "Repro retested: PASS/FAIL on <SHA>". If that is impossible, the close comment and the release notes say "Fix unverified end-to-end".

## 4. Review

- Each pull request gets one automated Codex review on its current head. A review of an earlier head does not count.
- P0 and P1 findings block the merge. A fix makes a new head, and that head gets its own review.
- P2 and P3 findings do not block. They go as checkboxes into one open follow-up issue per area and sprint, labelled `follow-up`. A finding that is already in that issue is not added again. The `P2` and `P3` labels are not used.
- A review by a worker or a tool is evidence, not authority to merge.

## 5. Merging

- Pull requests join `dev` as merge commits: `gh pr merge <number> --merge --delete-branch`. Never squash or rebase merge.
- Never use `--admin` or any override of a required check, and do not ask for one.
- Resolve conflicts on the pull request branch and rerun verification. `dev` and `main` only move forward and are never force-pushed.
- Merging into `dev` does not release or deploy anything.

## 6. Changelog

- `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and starts with an `## [Unreleased]` section.
- During the alpha, a pull request that changes what users get adds one line under `## [Unreleased]` in `CHANGELOG.md`. Write it for the person who uses LINA: what changed for them and why.
- A pull request that changes nothing users get carries the `no-changelog` label instead.
- At a release, the lines under `## [Unreleased]` are moved under a new `## [<version>] - <date>` heading in one commit.

## 7. Versions and releases

- During the alpha every version is `0.0.1-alpha.YYYYMMDD.N`: the base stays `0.0.1`, `YYYYMMDD` is the release date and `N` counts that day's releases from 1. The first is `0.0.1-alpha.20261102.1`.
- Python packages write the same version in PEP 440 form, `0.0.1aYYYYMMDD.postN` (for example `0.0.1a20261102.post1`; `0.0.1a20261102.1` is not valid PEP 440); the SemVer string is the one users see.
- Release tags are `v<version>`, for example `v0.0.1-alpha.20261102.1`. Release tags are immutable: never move or delete one.
- The owner decides when the alpha ends and what the first version after it is.
- Every release needs the owner's approval. A release commit stamps the version and the changelog together; the tag is made on that commit.
- lina keeps no upstream Hermes tags; its version history starts at `0.0.1-alpha.20261102.1`. See [docs/versioning.md](https://github.com/lina-system/lina/blob/dev/docs/versioning.md).

## 8. Authority

- The owner can merge any change and may reserve the merge of delegated work.
- When the owner delegates a scope (a project or a set of issues) to a worker, the worker may merge its pull requests in that scope once the review and verification conditions pass. Outside a delegated scope, merging needs the owner's explicit authorization.
- Every release and deployment needs the owner's approval.

## 9. Protected settings

These settings are enforced on lina, lina-app and lina-os:

- Merge commits only: squash and rebase merging are disabled.
- `dev` and `main` (and `upstream` in lina) refuse deletion and force push (repository ruleset). In lina, `dev` and `main` also require the checks listed in its `docs/delivery.md`.
- Branches are deleted after merge.
- Release tags are immutable.
- Secret scanning and push protection are on.
- The labels this policy and the repositories' merge gates use exist: `follow-up`, `no-changelog`, `dev-red-fix`, `dev-red-approved`, `no-issue`, `ui`.

## 10. Changing this policy

Change this policy through a pull request to this repository, under the rules above. Each repository's workflows, scripts and settings enforce it; update them together with it.
