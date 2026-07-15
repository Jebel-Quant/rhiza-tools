# Architecture

This page is the map for **where code goes** in `rhiza_tools`. The rationale
behind the layout lives in the Architecture Decision Records —
[ADR-0001](adr/0001-bump-my-version-adapter.md) (the bump-my-version adapter)
and [ADR-0005](adr/0005-command-module-split.md) (splitting command modules by
responsibility). This page is the living reference; the ADRs are the history.

## Layers

```
cli.py                          Typer surface — argument parsing, --help text, option wiring
  └─ commands/<command>/__init__.py  orchestration — the workflow for one command
       ├─ versioning.py         pure version math / bump-type resolution (no side effects)
       ├─ io.py                 project-file I/O, interactive prompts, public data models
       ├─ git.py                git plumbing (tag / commit / branch / push)
       └─ engine.py             third-party adapter (bump-my-version) — see ADR-0001
  └─ commands/<command>.py      single-file commands that never grew satellites
  └─ commands/_shared.py        helpers reused across commands
```

A command that has only one responsibility stays a single module
(`commands/<command>.py`); one that grows past the
[500-line gate](adr/0004-structural-meta-tests.md) (`tests/test_module_size.py`)
becomes a **subpackage** (`commands/<command>/`) whose `__init__.py` holds the
orchestration and whose siblings own the extracted responsibilities.

Dependencies point downward only: the orchestration `__init__.py` calls into its
sibling modules and `_shared`; the siblings do not import the package back.

## The command-subpackage convention

Inside a `commands/<command>/` subpackage, the file name tells you what lives
there:

| Module | Responsibility | Examples |
| ------ | -------------- | -------- |
| `__init__.py` | Typer-facing command orchestration — the entry point invoked from `cli.py` | `bump/__init__.py`, `release/__init__.py`, `rollback/__init__.py` |
| `versioning.py` | Pure version math and bump-type resolution; no I/O, no git | `bump/versioning.py`, `release/versioning.py` |
| `io.py` | Project-file reads/writes, interactive prompts/UI, and public data models (`BumpOptions`, `RollbackOptions`, `Language`) | `bump/io.py`, `rollback/io.py` |
| `git.py` | Git plumbing — tag/commit/branch lookups, pushes, working-tree checks | `bump/git.py`, `release/git.py`, `rollback/git.py` |
| `engine.py` | Adapter wrapping the `bump-my-version` library ([ADR-0001](adr/0001-bump-my-version-adapter.md)) | `bump/engine.py` |

Commands that never outgrew a single file stay flat: `version_matrix.py`,
`analyze_benchmarks.py`. Helpers used by
more than one command (git-command runner, remote-version lookup,
`pyproject.toml` validation) live in `commands/_shared.py`.

Extracted helpers are **re-exported** from the orchestration `__init__.py`, so
callers and tests keep importing `commands.bump.<helper>` /
`commands.release.<helper>` even after a move. When a moved function resolves a
dependency in its **new** module's namespace, the test patch target moves with
it (e.g. `commands.release.versioning.bump_command`,
`commands.rollback.git.run_git_command`).

## Where does my code go?

Work top-down through the first match:

1. **A new user-facing command?** Add a `@app.command` in `cli.py` (parsing +
   `--help`) and a `commands/<command>.py` orchestration module for the workflow.
   Promote it to a `commands/<command>/` subpackage only once it outgrows one
   file.
2. **Pure version/number logic** (parse, compare, compute the next version)? →
   `<command>/versioning.py`.
3. **Reads/writes project files or prompts the user?** → `<command>/io.py`.
4. **Shells out to git?** → `<command>/git.py`.
5. **Wraps `bump-my-version`?** → `<command>/engine.py`.
6. **Reused by more than one command?** → `_shared.py`.

Keep modules at or below the 500-line ceiling; when one approaches it, extract
the next responsibility into a sibling module within the subpackage and
re-export it from `__init__.py`. The current largest command module is ~380
lines.

## Tests mirror the package

`tests/` mirrors this layout: per-command tests live under
`tests/commands/<command>/` (e.g. `tests/commands/bump/`,
`tests/commands/release/`, `tests/commands/rollback/`), single-file command
tests sit directly in `tests/commands/`, and cross-cutting suites (CLI wiring,
end-to-end flows, structural meta-tests) stay at the `tests/` root. Test module
basenames are kept unique across the tree because pytest runs in `prepend`
import mode without `__init__.py` package markers.
