# Rollback

Rollback a release and/or version bump safely.

## Overview

The `rollback` command reverses release and bump operations by deleting release
tags from local and remote repositories, and optionally reverting the version
bump commit. It uses `git revert` (not `git reset`), making it safe even when
changes have already been pushed to remote.

## When to Use Rollback

Rollback is designed for **pre-publication** scenarios — i.e., before the
release workflow has completed and published artifacts. Common situations:

- **Accidental tag push** — You pushed a release tag before the code was ready.
  Deleting the remote tag stops the in-progress release workflow.
- **Wrong version bump** — You bumped to the wrong version (e.g., major instead
  of patch). Rollback reverts the bump commit and removes the tag so you can
  re-bump correctly.
- **Failed CI checks** — CI revealed issues after the tag was pushed but before
  the release workflow finalised.

### When Rollback Does Not Apply

Once the release workflow **completes successfully**, the following artifacts
exist and **cannot be reversed** by this command:

- **GitHub Release** — A published (non-draft) release with release notes and
  SBOM attachments.
- **PyPI package** — The wheel/sdist is published and PyPI does not allow
  re-uploading the same version. The version can only be
  [yanked](https://peps.python.org/pep-0592/), not deleted.
- **Devcontainer image** — The container image is pushed to the registry.

If a published release is broken, the recommended approach is to **release a
new patch version** with the fix rather than attempting to undo the release.

## Usage

```bash
# Rollback interactively (select from recent tags)
rhiza-tools rollback

# Rollback a specific release tag
rhiza-tools rollback v1.2.3

# Preview what would happen
rhiza-tools rollback v1.2.3 --dry-run

# Rollback and also revert the version bump commit
rhiza-tools rollback v1.2.3 --revert-bump

# Non-interactive mode (for CI/CD)
rhiza-tools rollback v1.2.3 --revert-bump -y
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `TAG` (argument) | *interactive* | Tag to rollback (e.g., `v1.2.3`). Omit for interactive selection |
| `--revert-bump` | `False` | Also revert the version bump commit |
| `--dry-run` | `False` | Print what would happen without executing |
| `--non-interactive` / `-y` | `False` | Skip all confirmation prompts |

## What Gets Rolled Back

The command performs these steps in order:

1. **Delete remote tag** — Removes the tag from the remote repository, which
   stops any in-progress release workflow triggered by the tag push.
2. **Delete local tag** — Removes the tag from the local repository.
3. **Revert bump commit** *(optional, with `--revert-bump`)* — Creates a new
   revert commit that undoes the version bump, restoring `pyproject.toml` and
   any other files modified by `bump-my-version`.
4. **Push revert commit** *(optional)* — Pushes the revert commit to remote.

## Safety Features

- **Non-destructive** — Uses `git revert` instead of `git reset`, preserving
  full git history and avoiding force-pushes.
- **Ordered operations** — Deletes the remote tag first to immediately stop
  any release workflow, before performing local cleanup.
- **Abort on failure** — If the remote tag deletion fails, remaining steps are
  skipped to prevent an inconsistent state.
- **Bump detection** — Automatically detects whether the tagged commit is a
  version bump commit and offers to revert it.
- **Dry-run support** — Preview the full rollback plan before executing.
- **Interactive confirmation** — Requires explicit confirmation before making
  changes (unless `--non-interactive` is used).

## Interactive Mode

When no tag argument is provided, the command shows a list of recent version
tags with their local/remote status:

```
? Select tag to rollback:
> v1.2.3 (local, remote)
  v1.2.2 (local, remote)
  v1.2.1 (local, remote)
```

## Rollback Plan Preview

Before executing, the command displays a rollback plan:

```
──────────────────────────────────────────────────
  Rollback Plan
──────────────────────────────────────────────────

  Tag to rollback: v1.2.3
  Commit:  abc123de
  Date:    2025-01-15 10:30:00
  Message: Bump version: 1.2.2 → 1.2.3

  Actions:
  1. Delete remote tag: git push origin :refs/tags/v1.2.3
  2. Delete local tag:  git tag -d v1.2.3
  3. Revert bump commit (creates a new revert commit)
  4. Push revert commit to remote

  Previous version: v1.2.2

──────────────────────────────────────────────────
```

## Common Scenarios

### Accidental Tag Push (Release Not Yet Published)

You pushed a release tag but the release workflow is still running or hasn't
started:

```bash
# Remove the tag and stop the release workflow
rhiza-tools rollback v1.2.3

# Later, when ready to release again
rhiza-tools release
```

### Wrong Version Bump (Before Release)

You bumped to the wrong version and tagged it, but the release workflow hasn't
published yet:

```bash
# Rollback both the tag and the bump commit
rhiza-tools rollback v1.2.3 --revert-bump

# Bump to the correct version and release
rhiza-tools release --with-bump --push
```

### CI/CD Rollback

Automate rollback in a CI/CD pipeline:

```bash
rhiza-tools rollback v1.2.3 --revert-bump -y
```

### Release Already Published

If the release workflow has already completed and artifacts are published,
rollback **will not** undo the published release or PyPI package. Instead,
fix the issue and release a new version:

```bash
# Fix the issue, then bump and release a patch
rhiza-tools release --with-bump --push
```

## Workflow

```
select tag → show plan → confirm → delete remote tag → delete local tag → revert bump (optional) → push revert (optional)
```
