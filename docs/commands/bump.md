# Bump Version

Bump the version of the project using semantic versioning.

## Overview

The `bump` command updates the version in `pyproject.toml` using
[bump-my-version](https://github.com/callowayproject/bump-my-version) and
[semver](https://semver.org/). You can provide an explicit version number, a
bump type, or leave it blank for an interactive prompt.

## Usage

```bash
# Interactive version selection
rhiza-tools bump

# Bump to a specific version
rhiza-tools bump 2.0.0

# Bump by type
rhiza-tools bump patch    # 1.2.3 -> 1.2.4
rhiza-tools bump minor    # 1.2.3 -> 1.3.0
rhiza-tools bump major    # 1.2.3 -> 2.0.0

# Preview changes without applying them
rhiza-tools bump minor --dry-run

# Bump and commit
rhiza-tools bump patch --commit

# Bump, commit, and push to remote
rhiza-tools bump minor --push
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `VERSION` (argument) | *interactive* | Version or bump type (`patch`, `minor`, `major`, `alpha`, `beta`, `rc`, `dev`) |
| `--dry-run` | `False` | Print what would happen without making changes |
| `--commit` | `False` | Commit the version change to git |
| `--push` | `False` | Push changes to remote after commit (implies `--commit`) |
| `--branch` | current branch | Branch to perform the bump on |
| `--allow-dirty` | `False` | Allow bumping with uncommitted changes |
| `--verbose` / `-v` | `False` | Show detailed output from bump-my-version |

## Interactive Mode

When no version argument is provided, the command enters interactive mode and
presents a menu of bump choices computed from the current version:

- **Patch** — increment the patch number
- **Minor** — increment the minor number
- **Major** — increment the major number
- **Alpha / Beta / RC / Dev** — create or increment a prerelease version

## Workflow

1. Reads the current version from `pyproject.toml`.
2. Validates the requested bump type or explicit version.
3. Calls bump-my-version to apply the change.
4. Optionally commits and pushes the change.
