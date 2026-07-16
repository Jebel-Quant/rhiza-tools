# CLAUDE.md

Guidance for Claude Code (and human contributors) working in this repository.

## What is this repo?

`rhiza-tools` is a shared CLI for Rhiza-managed projects. Its former commands
have all moved elsewhere in the ecosystem, so it **currently defines no
commands** (the CLI shell remains, published to PyPI). Its own development
infrastructure is synced from Rhiza.

> Commands that once lived here have been removed as their concerns moved
> elsewhere: release/versioning (`bump`, `release`, `rollback`, `update-readme`),
> the `pip-audit` / `suppression-audit` quality gates, `analyze-benchmarks`, and
> `version-matrix` (the CI matrix is now derived by
> `build-and-inspect-python-package`).

## Rhiza-managed files — do NOT edit directly

This project syncs its development infrastructure from the **Rhiza** template repo
(`jebel-quant/rhiza`). The configuration lives in
[`.rhiza/template.yml`](.rhiza/template.yml) (profile `github-project` + the `legal`
template).

**The files below are owned by Rhiza. Do not edit them directly here** — any local
change is overwritten on the next sync. To change one of them:

1. Make the change **upstream** in `jebel-quant/rhiza` (the relevant
   `bundles/<bundle>/...` source).
2. Cut a new Rhiza release.
3. Bump `ref:` in [`.rhiza/template.yml`](.rhiza/template.yml) here and run
   **`make sync`** (which invokes `rhiza sync`).

The authoritative, machine-generated list is the `files:` block of
[`.rhiza/template.lock`](.rhiza/template.lock), refreshed on every sync. Current
snapshot:

### Root
`.bandit`, `.editorconfig`, `.gitignore`, `.pre-commit-config.yaml`,
`.python-version`, `LICENSE`, `Makefile`, `SECURITY.md`, `pytest.ini`, `ruff.toml`

### `.github/`
- Workflows: `rhiza_benchmark.yml`, `rhiza_book.yml`, `rhiza_ci.yml`,
  `rhiza_codeql.yml`, `rhiza_marimo.yml`, `rhiza_release.yml`, `rhiza_sync.yml`,
  `rhiza_weekly.yml`, `rhiza_fuzzing.yml`, `rhiza_scorecard.yml`,
  `rhiza_mutation.yml` (opt-in mutation gate — `MUTATION_ENABLED`)
- `rulesets/main-branch-protection.json`, `rulesets/README.md` (branch
  protection — shipped by the `github` bundle)
- `dependabot.yml`, `release.yml`, `secret_scanning.yml`,
  `pull_request_template.md`
- `DISCUSSION_TEMPLATE/`, `ISSUE_TEMPLATE/`

> The list reflects the **current** rhiza template. This repo is pinned to an
> older `ref:`, so its `.rhiza/template.lock` snapshot is smaller — the extra
> files (`rhiza_fuzzing.yml`, `rhiza_scorecard.yml`, `rhiza_mutation.yml`,
> `.github/rulesets/*`) only land once you bump `ref:` and run `make sync`.

### `.rhiza/` (the sync engine — treat the whole directory as managed)
- `rhiza.mk`, `make.d/*.mk`, `requirements/*.txt`, `semgrep.yml`,
  `.cfg.toml`, `.env`, `.gitignore`, `.rhiza-version`
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `assets/`, `completions/`
- `tests/**` (the synced template test-suite)
- **Owned by you:** `.rhiza/template.yml` (and `.rhiza/template.lock`, which the
  tool regenerates).

### `docs/`
`docs/assets/rhiza-logo.svg`, `docs/development/MARIMO.md`,
`docs/development/TESTS.md`, `docs/index.md`, `docs/mkdocs-base.yml`

## Locally owned (safe to edit)

Everything **not** listed above — notably `pyproject.toml`, `README.md`, `uv.lock`,
`src/rhiza_tools/`, your own `tests/`, project-specific docs, and
`.rhiza/template.yml`. Project-specific Make hooks (`pre-install::`,
`post-install::`, …) go in the thin root `Makefile` above the `include` line.

> ⚠️ `.github/rulesets/main-branch-protection.json` is **no longer locally
> owned** — branch protection now ships via the `github` bundle. This repo's
> richer, matrix-specific ruleset will conflict on sync; either fold the generic
> parts upstream into rhiza or `exclude:` the bundle copy in `.rhiza/template.yml`
> to keep the local one. Same situation as `ruff.toml` (locally hardened here).
