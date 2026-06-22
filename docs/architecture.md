# Architecture

This page is the map for **where code goes** in `rhiza_tools`. The rationale
behind the layout lives in the Architecture Decision Records —
[ADR-0001](adr/0001-bump-my-version-adapter.md) (the bump-my-version adapter)
and [ADR-0005](adr/0005-command-module-split.md) (splitting command modules by
responsibility). This page is the living reference; the ADRs are the history.

## Layers

```
cli.py                     Typer surface — argument parsing, --help text, option wiring
  └─ commands/<command>.py  orchestration — the workflow for one command
       ├─ *_versioning.py   pure version math / bump-type resolution (no side effects)
       ├─ *_io.py           project-file I/O, interactive prompts, public data models
       ├─ *_git.py          git plumbing (tag / commit / branch / push)
       └─ *_engine.py       third-party adapter (bump-my-version) — see ADR-0001
  └─ commands/_shared.py    helpers reused across commands
```

Dependencies point downward only: orchestration modules call into the
suffixed modules and `_shared`; the suffixed modules do not import the
orchestration module back.

## The module-suffix convention

When a command module grows past the [500-line gate](adr/0004-structural-meta-tests.md)
(`tests/test_module_size.py`), a cohesive responsibility is extracted into a
sibling module named by **suffix**. The suffix tells you what lives there:

| Suffix | Responsibility | Examples |
| ------ | -------------- | -------- |
| _(none)_ | Typer-facing command orchestration — the entry point invoked from `cli.py` | `bump.py`, `release.py`, `rollback.py`, `version_matrix.py`, `generate_badge.py`, `update_readme.py`, `analyze_benchmarks.py` |
| `_versioning` | Pure version math and bump-type resolution; no I/O, no git | `bump_versioning.py`, `release_versioning.py` |
| `_io` | Project-file reads/writes, interactive prompts/UI, and public data models (`BumpOptions`, `RollbackOptions`, `Language`) | `bump_io.py`, `rollback_io.py` |
| `_git` | Git plumbing — tag/commit/branch lookups, pushes, working-tree checks | `bump_git.py`, `release_git.py`, `rollback_git.py` |
| `_engine` | Adapter wrapping the `bump-my-version` library ([ADR-0001](adr/0001-bump-my-version-adapter.md)) | `bump_engine.py` |
| `_shared` | Helpers used by more than one command (git-command runner, remote-version lookup, `pyproject.toml` validation) | `_shared.py` |

Extracted helpers are **re-exported** from the orchestration module, so callers
and tests keep importing `bump.<helper>` / `release.<helper>` even after a move.
When a moved function resolves a dependency in its **new** module's namespace,
the test patch target moves with it (e.g. `release_versioning.bump_command`,
`rollback_git.run_git_command`).

## Where does my code go?

Work top-down through the first match:

1. **A new user-facing command?** Add a `@app.command` in `cli.py` (parsing +
   `--help`) and a `commands/<command>.py` orchestration module for the workflow.
2. **Pure version/number logic** (parse, compare, compute the next version)? →
   `*_versioning.py`.
3. **Reads/writes project files or prompts the user?** → `*_io.py`.
4. **Shells out to git?** → `*_git.py`.
5. **Wraps `bump-my-version`?** → `*_engine.py`.
6. **Reused by more than one command?** → `_shared.py`.

Keep modules at or below the 500-line ceiling; when one approaches it, extract
the next responsibility into a suffixed sibling and re-export. The current
largest command module is ~380 lines.
