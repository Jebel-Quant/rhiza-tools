# Update README

Update `README.md` with the current output from `make help`.

## Overview

The `update-readme` command runs `make help` and replaces the corresponding
section in `README.md` with the latest help output, keeping documentation in
sync with available Make targets.

## Usage

```bash
# Update README with make help output
rhiza-tools update-readme

# Preview changes without modifying README
rhiza-tools update-readme --dry-run
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--dry-run` | `False` | Print the help output that would be inserted without modifying `README.md` |

## How It Works

1. Runs `make help` and captures the output.
2. Strips ANSI colour codes and Make directory messages.
3. Locates the help section markers in `README.md`.
4. Replaces the content between the markers with the fresh output.
