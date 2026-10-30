# lina-system repository policy

This policy applies to every lina-system repository: lina, lina-app and lina-os. It sets the common rules for branches, pull requests, verification, review, merging, the changelog, versions and releases.

The branch, merge, changelog and release rules follow those of [omo](https://github.com/code-yeongyu/oh-my-openagent) ([release process](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/release-process.md)). Each repository adds what is specific to it, such as its build, test and QA commands, in its own CONTRIBUTING. A repository's docs may add to this policy but not contradict it.

A worker is a coding tool or agent working on a repository.

## 1. Branches

- `dev` is the default and integration branch. Every pull request targets `dev`.
- `main` is the release branch. Only the release workflow moves it. Pull requests into `main` are refused.
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
- Every required check is green on the current head before merge.
- A required check that is already red on `dev` is a defect of `dev` and still blocks the merge. Reproduce it, fix the cause in this pull request or a separate one, and rerun every required check.
- Never make a check pass by skipping tests, weakening assertions, adding retries, `continue-on-error`, excluding a platform or working around one environment. A smaller failure count is not a green result.
- Tests assert behaviour: state, IDs, structured fields, exit codes and events. They wait for an observed event, never a fixed sleep. Do not pin prose with a test.
- A fix for a race or concurrency bug closes its issue only after the original reproducer passes on the fix commit, recorded in the issue as "Repro retested: PASS/FAIL on <SHA>". If that is impossible, the close comment and the release notes say "Fix unverified end-to-end".

## 4. Review

- Each pull request gets one automated review on its current head. A review of an earlier head does not count.
- P0 and P1 findings block the merge. A fix makes a new head, and that head gets its own review.
- P2 and P3 findings do not block. They become follow-up issues labelled `follow-up` and `P2` or `P3`.
- A review by a worker or a tool is evidence, not authority to merge.

## 5. Merging

- Pull requests join `dev` as merge commits: `gh pr merge <number> --merge --delete-branch`. Never squash or rebase merge.
- Never use `--admin` or any override of a required check, and do not ask for one.
- Resolve conflicts on the pull request branch and rerun verification. `dev` and `main` only move forward and are never force-pushed.
- Merging into `dev` does not release or deploy anything.

## 6. Changelog

- Never edit `CHANGELOG.md` in a normal pull request.
- A pull request that changes what users get adds exactly one file, `changes/unreleased/<pr-number>.md`, with the entry for the next release. Write it for the person who uses LINA: what changed for them and why.
- A pull request that changes nothing users get carries the `no-changelog` label instead.
- An existing fragment is never edited by another pull request.
- Only the release-state pull request (branch `release/v<version>`) assembles the fragments into `CHANGELOG.md` and deletes them, in one commit.
- `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 7. Versions and releases

- Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Release tags are `v<version>`. A prerelease such as `0.2.0-beta.3` goes to the `beta` channel; a stable version goes to `latest`.
- A release is made only by the repository's `publish` workflow, dispatched by the owner with `patch`, `minor`, `major` or an explicit version. Until a repository has that workflow, it has no releases.
- The workflow runs the release gates, calculates the version, stamps the version and the changelog on `release/v<version>`, opens and merges that release-state pull request into `dev`, tags `v<version>` on the merged commit, publishes from that exact commit with provenance, creates the GitHub release and advances `main` to the tag.
- Release gates: required checks green on the prepared commit, targeted tests for changed code, documentation covering new public behaviour, and known issues written into the release notes.
- Never change a version number by hand, publish a package by hand, or create, move or delete a release tag by hand. Release tags are immutable.
- A failed publish is resumed, not repeated. Rerun the failed jobs of the run that owns them (`gh run rerun --failed <run-id>`). Once a release commit, tag or publication exists, continue that attempt instead of dispatching a new one. Dispatch a fresh run only before any release state exists, or when the source, workflow or inputs must change.

## 8. Authority

- The owner can merge any change and may reserve the merge of delegated work.
- When the owner delegates a scope (a project or a set of issues) to a worker, the worker may merge its pull requests in that scope once the review and verification conditions pass. Outside a delegated scope, merging needs the owner's explicit authorization.
- Every release and deployment needs the owner's approval; dispatching `publish` is that approval.

## 9. Protected settings

These settings are enforced on lina, lina-app and lina-os:

- Merge commits only: squash and rebase merging are disabled.
- `dev` and `main` refuse deletion and force push.
- Release tags are immutable.
- Secret scanning and push protection are on.
- The labels this policy uses exist: `follow-up`, `P2`, `P3`, `no-changelog`.

## 10. Changing this policy

Change this policy through a pull request to this repository, under the rules above. Each repository's workflows, scripts and settings enforce it; update them together with it.
