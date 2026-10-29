# lina-system repository policy

This policy applies to every lina-system repository. It sets the common rules for branches, review, verification, merging, authority and protected history.

Each repository keeps what is specific to it, such as its gate, scripts, release process and labels, in its own CONTRIBUTING and `docs/policy/`.

A worker is a coding tool working on a repository.

## 1. Branches and pull requests

Each repository has one integration branch: its default branch, `dev` for lina and `main` elsewhere. Pull requests target it.

Use a short-lived branch from the latest integration branch with one coherent change. Keep unrelated refactoring and behavior changes separate. Reviewability and safe rollback matter more than line count. Coordinate edits that overlap work on another branch.

Check the owner and linked worktrees before deleting an integrated branch. Preserve unintegrated work until its disposition is agreed.

Open one pull request per issue. Link the issue with `Closes #<number>` and describe the change and its verification. The body follows the repository's pull request template, or this organization's default. Issues follow the [issue format](https://github.com/lina-system/devflow/blob/main/docs/issue-format.md).

Branch names, commit messages, pull request titles and merge commit messages are in English, regardless of the language used to request the work. Commit and pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), for example `docs: clarify integration steps` or `fix: handle empty input`. Quoted source text, logs, and code stay unchanged.

The pull request description and merge commit message carry what a reader needs later:

- The problem, the approach, and relevant issue links.
- Tests or manual checks performed, with results and any gaps.
- Compatibility, migration, and recovery implications when applicable.

## 2. Review

Obtain one automated review pass on the current head and address blocking findings. Each repository names its reviewer in its own docs. A review of an earlier head does not count for the current head.

- P0 and P1 findings block the merge. A fix makes a new head, and that head gets its own single pass.
- A clean review is a pass on the current head with no P0 or P1 findings.
- P2 and P3 findings do not block. They become follow-up issues, labelled `follow-up` and `P2` or `P3`, as the issue format describes.
- Do not start repeated review loops. A head that already has a review pass does not get another.

## 3. Verification shape (CI)

Each repository names, in its CONTRIBUTING, one required gate check and the local command that runs it, for example lina's `foundation` check, run locally with `node scripts/foundation.mjs`. Run the gate locally before opening a pull request. The gate passes only when every check it selected passed for that exact head.

Every repository follows the same shape:

- Pull requests run a fast lane plus the cases affected by the change range. The range runs from the pull request's base to its merge commit, so the proposed result is verified even when the branch is behind the integration branch.
- Pushes to the integration branch run the full suite, on the newest commit only.
- macOS runs only on pull requests that touch macOS paths, as one job, and in the nightly run.
- Post-merge failures open or update one `qa` issue per failing test. They do not block unrelated pull requests.

Verification jobs have read-only repository permissions and do not push branches. A separate post-merge QA job can write issues; pull request runs never execute its reporter.

For runnable changes, show evidence from the affected usage path, not only unit tests. For documentation, reading and link and format checks are appropriate; do not write tests that pin prose.

## 4. Merging

- Changes join the integration branch as merge commits. Never squash or rebase.
- The integration branch only moves forward.
- Bring a branch up to date by merging the integration branch into it when needed, resolve conflicts on the branch, and rerun verification.
- An authorized merger (see Authority) merges the pull request once its current head has a green gate and a clean review.
- Where a repository runs an integration script or lander, that path is the way in: lina's `scripts/integrate.mjs`, and devflow's lander once it is enabled.

An integration script or lander applies the same conditions. It verifies the merge candidate before it advances the integration branch. When the merge conflicts or the gate fails, the integration branch stays where it was and the script or lander reports why. It never force-pushes.

Integrating a change does not publish a release or deploy the product.

## 5. Authority

The owner can merge any change and may reserve the merge of delegated work. Otherwise, when the owner delegates a scope (a project or a set of issues) to a worker, the worker may merge its pull requests in that scope once the review and gate conditions pass. Outside a delegated scope, merging needs the owner's explicit authorization. A repository's local integration script is the owner's path. Every release and deployment needs the owner's approval.

A review by a worker or another tool is supporting evidence; it grants no integration authority. Record what a review checked and what it could not establish.

## 6. Protected history and settings

These settings are enforced on the code repositories (lina, lina-app, devflow, lina-os and lina-world):

- Merge commits only: squash and rebase merging are disabled.
- The default and release branches (`main`, and lina's `dev`) refuse deletion and force push.
- Release tags are immutable.
- Secret scanning push protection is on.

Design documents and the review and fix history of a change are kept. Protected branches are never rewritten, and scripts and landers never force-push.

## 7. Changing this policy

Change this policy through a pull request to this repository, under the rules above. A repository's docs may add to it but not contradict it.

Each repository's workflows, scripts and settings enforce this policy. Update this policy, or the repository's own docs, alongside any authorized change to them.
