# 0002 — Fold the regenerated CHANGELOG into the bump commit

- Status: Accepted
- Deciders: rhiza-tools maintainers

## Context

When the project uses [git-cliff](https://git-cliff.org/) for changelogs, the
`CHANGELOG.md` must be regenerated for each new version. The obvious approach —
regenerate and push the changelog as its own commit on the default branch — has
two problems in this project's setup:

1. A separate push to the default branch is blocked by branch-protection
   rulesets.
2. It counts as an unreviewed change against the OpenSSF Scorecard Code-Review
   check.

## Decision

`bump/engine.py`'s `_build_changelog_hooks` emits git-cliff commands as bump-my-version
`pre_commit_hooks`:

```
uvx git-cliff --tag v<new_version> --output CHANGELOG.md
git add CHANGELOG.md
```

bump-my-version runs these hooks and commits whatever is staged as part of the
version-bump commit — the same mechanism already used to fold in `uv.lock`. The
result is that the version bump, the lockfile, and the changelog land in a
single commit and tag, with no separate push.

The hooks are emitted only when the project is configured for git-cliff (a
`cliff.toml` / `.cliff.toml` is present), so projects without changelog tooling
are unaffected. The new version is passed with `--tag` because the release tag
does not exist yet when the hooks run; otherwise git-cliff would file the new
entries under "unreleased".

## Consequences

- One reviewable, atomic commit+tag per release; no default-branch side-push.
- Compatible with branch protection and the Scorecard Code-Review check.
- Behavior is gated on changelog tooling being present, so it is opt-in by
  project configuration.
