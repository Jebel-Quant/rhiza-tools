# Releasing

Guide to the `bump` and `release` commands provided by `rhiza-tools`.

## Overview

`rhiza-tools` provides two commands for version management:

- **`bump`** — updates the version in `pyproject.toml` using semantic versioning
- **`release`** — validates the repository state and pushes a release tag to trigger CI/CD

## Bump Command

### Flow

```mermaid
flowchart TD
    start([rhiza-tools bump]) --> check_pyproject{pyproject.toml exists?}
    check_pyproject -->|No| error_exit[Exit with error]
    check_pyproject -->|Yes| read_version[Read current version]
    read_version --> version_arg{Version argument provided?}

    version_arg -->|No| interactive[Interactive prompt:<br/>patch, minor, major,<br/>alpha, beta, rc, dev]
    version_arg -->|Bump type<br/>e.g. patch| calc_next[Calculate next version]
    version_arg -->|Explicit version<br/>e.g. 1.2.3| validate_semver{Valid semver?}

    interactive --> new_version[New version determined]
    calc_next --> new_version
    validate_semver -->|Yes| new_version
    validate_semver -->|No| error_exit

    new_version --> dry_run{--dry-run?}
    dry_run -->|Yes| show_diff[Show what would change]
    dry_run -->|No| write_version[Write version to pyproject.toml]
    write_version --> commit{--commit?}
    commit -->|Yes| git_commit[Git commit + tag]
    commit -->|No| done([Done])
    git_commit --> push{--push?}
    push -->|Yes| git_push[Push to remote]
    push -->|No| done
    git_push --> done
```

### Usage

```bash
# Interactive (prompts for bump type)
rhiza-tools bump

# Specific bump type
rhiza-tools bump patch
rhiza-tools bump minor
rhiza-tools bump major

# Prerelease
rhiza-tools bump alpha
rhiza-tools bump beta
rhiza-tools bump rc

# Explicit version
rhiza-tools bump 2.0.0

# Preview changes
rhiza-tools bump minor --dry-run
```

### Options

| Option          | Description                                           |
|-----------------|-------------------------------------------------------|
| `VERSION`       | Target version or bump type (or omit for interactive) |
| `--dry-run`     | Show what would change without modifying files        |
| `--commit`      | Automatically commit the version change               |
| `--push`        | Push changes to remote after commit                   |
| `--branch`      | Branch to perform the bump on                         |
| `--allow-dirty` | Allow bumping with uncommitted changes                |
| `--verbose`     | Show detailed bump-my-version output                  |

## Release Command

### Flow

```mermaid
flowchart TD
    start([rhiza-tools release]) --> check_pyproject{pyproject.toml exists?}
    check_pyproject -->|No| error_exit[Exit with error]
    check_pyproject -->|Yes| get_branch[Get current branch]

    get_branch --> bump_decision{--bump or --with-bump?}
    bump_decision -->|--bump TYPE| auto_bump[Bump version to TYPE]
    bump_decision -->|--with-bump| interactive_bump[Interactive bump selection]
    bump_decision -->|Neither| ask_bump{Ask: bump before release?}

    ask_bump -->|Yes| interactive_bump
    ask_bump -->|No| skip_bump[Skip bump]

    auto_bump --> get_version
    interactive_bump --> get_version
    skip_bump --> get_version

    get_version[Read version from pyproject.toml] --> check_state

    subgraph check_state [Pre-flight Checks]
        clean{Working tree clean?}
        uptodate{Branch up-to-date?}
        tag_local{Tag exists locally?}
        tag_remote{Tag exists on remote?}
    end

    clean -->|No| error_exit
    clean -->|Yes| uptodate
    uptodate -->|No| error_exit
    uptodate -->|Yes| tag_local
    tag_local -->|No| error_exit
    tag_local -->|Yes| tag_remote
    tag_remote -->|Yes| error_exit
    tag_remote -->|No| confirm

    confirm{Confirm push?} -->|Yes| push_tag[Push tag to origin]
    confirm -->|No| cancelled[Cancelled]

    push_tag --> success([Release workflow triggered])
```

### Usage

```bash
# Interactive (prompts for bump and push)
rhiza-tools release

# Bump and release in one step
rhiza-tools release --bump PATCH --push

# Interactive bump selection with dry-run preview
rhiza-tools release --with-bump --push --dry-run

# Non-interactive (for CI/CD)
rhiza-tools release --bump MINOR --push --non-interactive
```

### Options

| Option               | Description                                          |
|----------------------|------------------------------------------------------|
| `--bump TYPE`        | Bump type (`MAJOR`, `MINOR`, `PATCH`) before release |
| `--with-bump`        | Interactively select bump type before release        |
| `--push`             | Push changes to remote                               |
| `--dry-run`          | Preview without making changes                       |
| `--non-interactive`  | Skip all confirmation prompts (for CI/CD)            |

## CI/CD Pipeline

Once the tag is pushed, the automated pipeline takes over:

```mermaid
flowchart LR
    tag[Tag pushed] --> validate[Validate]
    validate --> build[Build]
    build --> draft[GitHub Release]
    draft --> pypi[Publish to PyPI]
    pypi --> done([Complete])
```

## Troubleshooting

| Problem                        | Solution                                          |
|--------------------------------|---------------------------------------------------|
| "Uncommitted changes" error    | Commit or stash changes before releasing          |
| "Branch behind remote" error   | Pull the latest changes: `git pull`               |
| "Tag already exists" error     | The version was already released; bump again      |
| Release workflow not triggered | Ensure the tag matches `v*` (e.g., `v1.2.3`)     |

