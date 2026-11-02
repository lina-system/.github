## Summary

- What changed for the person or the maintainer, and why.

Closes #

## Verification

- What you ran on the real surface and what you observed.
- Screen changes: attach a capture.

## Risk

- What could still go wrong, and what was not checked.

## Checklist

- [ ] Scope stays on the linked issue; no unrelated cleanup.
- [ ] A change users get adds one line under `## [Unreleased]` in `CHANGELOG.md`; otherwise the `no-changelog` label applies.
- [ ] Docs updated where behaviour or contracts changed.
- [ ] Secrets, auth and unsafe defaults reviewed.
- [ ] Merges into `dev` with a merge commit after green checks and a clean review ([policy](https://github.com/lina-system/.github/blob/main/POLICY.md)).
