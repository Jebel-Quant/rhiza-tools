# Configuration

`rhiza-tools` reads its configuration from `.rhiza/.cfg.toml` in the project
root. This file controls how [bump-my-version](https://github.com/callowayproject/bump-my-version)
operates when you run `rhiza-tools bump` or `rhiza-tools release --with-bump`.

## File Location

```
your-project/
├── .rhiza/
│   └── .cfg.toml      ← configuration file
├── pyproject.toml
└── ...
```

The path is defined by `CONFIG_FILENAME` in `rhiza_tools.config` and defaults
to `.rhiza/.cfg.toml`.

## Full Reference

Below is a fully annotated example with the default values:

```toml
[tool.bumpversion]
# Regex to parse version components from the current version string.
# Supports: major.minor.patch, prerelease (e.g. 1.0.0-alpha.1),
# and build metadata (e.g. 1.0.0+build.42).
parse = """(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)\
(?:-(?P<release>[a-z]+)\\.(?P<pre_n>\\d+))?\
(?:\\+build\\.(?P<build_n>\\d+))?"""

# Serialization templates, tried in order. The first template whose
# placeholders are all present is used to render the new version string.
serialize = [
    "{major}.{minor}.{patch}-{release}.{pre_n}+build.{build_n}",
    "{major}.{minor}.{patch}+build.{build_n}",
    "{major}.{minor}.{patch}-{release}.{pre_n}",
    "{major}.{minor}.{patch}",
]

# How to locate the old version in files.
search = "{current_version}"
replace = "{new_version}"

# Whether to use regex for search/replace in files.
regex = false

# Skip errors when a file doesn't contain the version string.
ignore_missing_version = false

# Skip errors when a configured file doesn't exist.
ignore_missing_files = false

# Create an annotated git tag after bumping.
tag = true

# GPG-sign the tag.
sign_tags = false

# Tag name template. {new_version} is replaced with the bumped version.
tag_name = "v{new_version}"

# Tag message template.
tag_message = "Bump version: {current_version} → {new_version}"

# Allow bumping when the working tree has uncommitted changes.
allow_dirty = false

# Automatically commit the version change.
commit = true

# Commit message template.
message = "Chore: bump version {current_version} → {new_version}"

# Extra arguments passed to `git commit`.
commit_args = ""

# Commands to run before the bump commit is created.
# Useful for regenerating lock files or running formatters.
pre_commit_hooks = ["uv sync", "git add uv.lock"]
```

### Prerelease Parts

The `[tool.bumpversion.parts.release]` section defines the prerelease
lifecycle. Versions progress through these values in order:

```toml
[tool.bumpversion.parts.release]
# The value that means "this is a production release" (i.e. no prerelease tag).
optional_value = "prod"

# Ordered progression of prerelease stages.
values = [
    "dev",
    "alpha",
    "beta",
    "rc",
    "prod",
]
```

For example, bumping `alpha` on version `1.0.0` produces `1.0.1-alpha.1`.
Subsequent `alpha` bumps increment the pre-release number: `1.0.1-alpha.2`.
Bumping `beta` advances the stage: `1.0.1-beta.1`.

### File Targets

Specify which files contain the version string. Each `[[tool.bumpversion.files]]`
entry can override `search` and `replace` patterns:

```toml
[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'

# Add more files as needed:
# [[tool.bumpversion.files]]
# filename = "src/my_package/__init__.py"
# search = '__version__ = "{current_version}"'
# replace = '__version__ = "{new_version}"'
```

## Key Settings Explained

### `tag`

When `true`, `bump-my-version` creates an annotated git tag (e.g. `v1.2.4`)
after committing the version change. The `release` command expects this tag to
exist locally before pushing it to the remote. **Keep this set to `true`** if
you use `rhiza-tools release`.

### `commit`

When `true`, the version change is automatically committed. The `release`
command requires a clean working tree, so this should normally stay `true`.

### `pre_commit_hooks`

Commands that run before the bump commit. The default hooks run `uv sync` to
update `uv.lock` and stage the lock file so it's included in the commit.

### `tag_name`

Controls the tag format. The default `v{new_version}` produces tags like
`v1.2.3`. The release command and CI/CD workflows expect tags matching the
`v*` pattern.

## Loading Configuration Programmatically

```python
from rhiza_tools.config import load_config

config = load_config()

# Access bumpversion settings
bv = config.bumpversion
print(bv.get("tag_name"))  # "v{new_version}"

# Access arbitrary keys
value = config.get("custom_key", "default")
```

You can also pass a custom path:

```python
from pathlib import Path
from rhiza_tools.config import load_config

config = load_config(Path("custom/.cfg.toml"))
```
