# 0001 — Isolate bump-my-version behind an adapter

- Status: Accepted
- Deciders: rhiza-tools maintainers

## Context

The `bump` command drives [bump-my-version](https://github.com/callowayproject/bump-my-version)
to rewrite version strings, commit, and tag. bump-my-version exposes internals
we depend on directly: `bumpversion.bump.do_bump`, `bumpversion.config.get_configuration`,
`bumpversion.ui.setup_logging`, the `Config` model (its `files_to_modify` and
`pre_commit_hooks` fields), and the `BumpVersionError` exception hierarchy.

These are not a stable public API. If they were referenced from many places, an
upstream change would force edits scattered across the codebase, and we would
likely discover the break only when a real release failed.

## Decision

All contact with bump-my-version internals lives in a single module,
`rhiza_tools.commands.bump.engine`. Every other module goes through the helpers
it exposes (`_build_configuration`, `_preflight_bump`, `_execute_bump`, …). The
module is typed against bump-my-version's concrete `Config` (aliased
`BumpConfig`) rather than `Any`, because `do_bump` requires that exact type, so
the adapter must hold a real `Config` anyway — using it keeps the surface fully
checked under strict `ty`.

A contract test, `tests/test_bumpversion_contract.py`, pins the exact upstream
surface the adapter relies on (the `pre_commit_hooks` and `files_to_modify`
fields, and the importable `BumpVersionError` base). It inspects model fields
only and never runs a full bump, so it is cheap and fails loudly at CI time if
upstream renames or retypes anything.

## Consequences

- An upstream change is reconciled in exactly one module, and the contract test
  flags it before it can corrupt a release.
- Exception handling in the adapter is narrowed to the domains upstream actually
  raises (`BumpVersionError`, plus `ValueError`/`OSError` for config loading)
  rather than a blanket `except Exception` — see the adapter's inline notes.
- The rest of the codebase never imports from `bumpversion.*`.
