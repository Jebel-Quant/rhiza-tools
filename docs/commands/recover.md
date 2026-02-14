# Recover

Recover (rollback) a release and/or version bump safely.

## Overview

The `recover` command reverses release and bump operations by deleting release
tags from local and remote repositories, and optionally reverting the version
bump commit. It uses `git revert` (not `git reset`), making it safe even when
changes have already been pushed to remote.

## Usage

```bash
# Recover interactively (select from recent tags)
rhiza-tools recover

# Recover a specific release tag
rhiza-tools recover v1.2.3

# Preview what would happen
rhiza-tools recover v1.2.3 --dry-run

# Recover and also revert the version bump commit
rhiza-tools recover v1.2.3 --revert-bump

# Non-interactive mode (for CI/CD)
rhiza-tools recover v1.2.3 --revert-bump -y
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `TAG` (argument) | *interactive* | Tag to recover (e.g., `v1.2.3`). Omit for interactive selection |
| `--revert-bump` | `False` | Also revert the version bump commit |
| `--dry-run` | `False` | Print what would happen without executing |
| `--non-interactive` / `-y` | `False` | Skip all confirmation prompts |

## What Gets Recovered

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
- **Dry-run support** — Preview the full recovery plan before executing.
- **Interactive confirmation** — Requires explicit confirmation before making
  changes (unless `--non-interactive` is used).

## Interactive Mode

When no tag argument is provided, the command shows a list of recent version
tags with their local/remote status:

```
? Select tag to recover (rollback):
> v1.2.3 (local, remote)
  v1.2.2 (local, remote)
  v1.2.1 (local, remote)
```

## Recovery Plan Preview

Before executing, the command displays a recovery plan:

```
──────────────────────────────────────────────────
  Recovery Plan
──────────────────────────────────────────────────

  Tag to recover: v1.2.3
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

### Accidental Release

You pushed a release tag but the release was premature:

```bash
# Remove the tag and stop the release workflow
rhiza-tools recover v1.2.3

# Later, when ready to release again
rhiza-tools release
```

### Wrong Version Bump

You bumped to the wrong version and released:

```bash
# Rollback both the tag and the bump commit
rhiza-tools recover v1.2.3 --revert-bump

# Bump to the correct version and release
rhiza-tools release --with-bump --push
```

### CI/CD Rollback

Automate rollback in a CI/CD pipeline:

```bash
rhiza-tools recover v1.2.3 --revert-bump -y
```

## Workflow

```
select tag → show plan → confirm → delete remote tag → delete local tag → revert bump (optional) → push revert (optional)
```
