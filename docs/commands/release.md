# Release

Push a release tag to remote to trigger the release workflow.

## Overview

The `release` command validates the git repository state and pushes the git tag
for the current version to the remote, which triggers the automated release
workflow (GitHub Actions). Optionally, it can bump the version before creating
the release.

## Usage

```bash
# Push a release tag (with prompts)
rhiza-tools release

# Preview what would happen
rhiza-tools release --dry-run

# Non-interactive mode (for CI/CD)
rhiza-tools release --non-interactive

# Bump version and release in one step
rhiza-tools release --bump MINOR --push

# Interactive bump with dry-run preview
rhiza-tools release --with-bump --push --dry-run
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--bump` | `None` | Bump type (`MAJOR`, `MINOR`, `PATCH`) before release |
| `--with-bump` | `False` | Interactively select bump type before release |
| `--push` | `False` | Push changes to remote without prompting |
| `--dry-run` | `False` | Print what would happen without executing |
| `--non-interactive` / `-y` | `False` | Skip all confirmation prompts |

## Pre-flight Checks

Before pushing the tag, the command validates:

1. **Clean working tree** — no uncommitted changes.
2. **Branch is up-to-date** — not behind remote.
3. **Tag exists locally** — the version tag was created by bump-my-version.
4. **Tag not already on remote** — prevents duplicate releases.

## Workflow

```
bump (optional) → validate repo → push tag → GitHub Actions release
```
