# 0005 — Split large command modules by responsibility

- Status: Accepted
- Deciders: rhiza-tools maintainers

## Context

Command modules naturally mix three concerns: the Typer command surface and
orchestration, version/bump logic, and git plumbing. Left together they grow
past the size at which a file is easy to reason about (the original `bump.py`
crossed this line in #207).

## Decision

When a command module grows large, extract a cohesive responsibility into a
sibling module and **re-export** the moved names from the original module so the
public import surface — and existing tests — are unchanged. The established
pattern:

| Command | Surface / orchestration | Extracted module(s) |
| ------- | ----------------------- | ------------------- |
| `bump` | `bump.py` | `bump_versioning.py`, `bump_engine.py` (the adapter, [ADR-0001](0001-bump-my-version-adapter.md)) |
| `release` | `release.py` | `release_versioning.py` (bump-type resolution) |
| `rollback` | `rollback.py` | `rollback_git.py` (git tag/commit plumbing) |

Because the helpers are re-exported, callers and tests continue to import
`release.<helper>` / `rollback.<helper>`. When a moved function looks up a
dependency in its **new** module's namespace, the corresponding test patch
target moves with it (e.g. `release_versioning.bump_command`,
`rollback_git.run_git_command`).

The [`test_module_size`](0004-structural-meta-tests.md) gate enforces the
ceiling that triggers this; after the #223 split the largest command module is
~700 lines and the gate is set to 750.

## Consequences

- Each module has a single clear responsibility and stays navigable.
- The re-export convention keeps refactors non-breaking for importers.
- Splitting interacts with the test suite's module-namespace patching: moving
  code requires moving the patch target to where the dependency now resolves.
